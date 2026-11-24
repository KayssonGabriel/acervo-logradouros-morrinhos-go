import argparse
from collections import Counter, defaultdict
from contextlib import closing
import csv
from io import TextIOWrapper
import json
from pathlib import Path
import re
import sqlite3
from zipfile import BadZipFile, ZipFile

from acervo import BANCO, abrir_banco
from busca import chave


CSV_IBGE = '5213806_MORRINHOS.csv'
CAMPOS_IBGE = {'COD_MUNICIPIO', 'DSC_LOCALIDADE', 'NOM_TIPO_SEGLOGR', 'NOM_TITULO_SEGLOGR', 'NOM_SEGLOGR'}
SEM_NOME = re.compile(r'\bsem (?:denominacao|nome|numeracao)\b|^(?:s n|sn)$')
TIPOS_VIA = {'rua', 'avenida', 'alameda', 'praca', 'viela', 'travessa', 'acesso', 'beco',
             'passagem', 'estrada', 'rodovia', 'via', 'lateral', 'marginal', 'saida', 'caminho'}


def cobertura(db):
    fonte = db.execute('''SELECT id, referencia FROM fonte WHERE tipo = 'lista_postal' AND abrangencia = 'integral'
                          ORDER BY referencia DESC, prioridade DESC, id LIMIT 1''').fetchone()
    if fonte is None:
        raise ValueError('Importe uma lista integral antes de auditar.')
    linhas = db.execute('''
        SELECT o.bairro_original, o.nome_chave, c.situacao_historico, c.divergencia_postal,
               c.conferencia_correios, c.observacao_postal_id, o.id
        FROM observacao_postal_v1 o JOIN consulta_v1 c ON c.trecho_id = o.trecho_canonico_id
        WHERE o.fonte_id = ? ORDER BY o.bairro_original, o.nome_chave
    ''', (fonte['id'],)).fetchall()
    por_bairro = defaultdict(Counter)
    for linha in linhas:
        contagem = por_bairro[linha['bairro_original'] or 'Localidade a identificar']
        contagem['registros'] += 1
        contagem[linha['situacao_historico']] += 1
        if linha['divergencia_postal']:
            contagem['divergencia_em_fontes'] += 1
        contagem['conferidos_nos_correios'] += linha['conferencia_correios'] == 'confirmado' and linha['observacao_postal_id'] == linha['id']
    estados = dict(db.execute('SELECT situacao_postal, count(*) FROM consulta_v1 GROUP BY situacao_postal'))
    por_bairro = [{"bairro": bairro, **contagem} for bairro, contagem in por_bairro.items()]
    por_bairro.sort(key=lambda linha: (-linha.get('historico_a_confirmar', 0), chave(linha['bairro'])))
    resumo = {'ultima_lista_integral': fonte['id'], 'registros_da_lista_integral': len(linhas),
              'situacao_postal': estados, 'por_bairro': por_bairro,
              'registros_de_atos': db.execute('SELECT count(*) FROM ato_nome').fetchone()[0],
              'conferencias_diretas_registradas': db.execute('SELECT count(*) FROM conferencia_correios').fetchone()[0]}
    anterior = db.execute('''SELECT id FROM fonte
        WHERE tipo = 'lista_postal' AND abrangencia = 'integral' AND referencia < ?
        ORDER BY referencia DESC, prioridade DESC, id LIMIT 1''', (fonte['referencia'],)).fetchone()
    if anterior:
        resumo['comparacao_listas_integrais'] = comparar_edicoes(db, anterior['id'], fonte['id'])
    return resumo, linhas


def comparar_edicoes(db, anterior, atual):
    def rotulos(fonte):
        por_cep = defaultdict(set)
        for linha in db.execute('SELECT cep, nome_chave, bairro_original FROM observacao_postal WHERE fonte_id = ?',
                                (fonte,)):
            por_cep[linha['cep']].add((linha['nome_chave'], chave(linha['bairro_original'])))
        return por_cep

    antigos, recentes = rotulos(anterior), rotulos(atual)
    comuns = antigos.keys() & recentes.keys()
    return {'anterior': anterior, 'atual': atual, 'ceps_presentes_nas_duas': len(comuns),
            'ceps_so_na_anterior': sorted(antigos.keys() - recentes.keys()),
            'ceps_so_na_atual': sorted(recentes.keys() - antigos.keys()),
            'ceps_com_rotulos_diferentes': sum(antigos[cep] != recentes[cep] for cep in comuns)}


def cruzar_cnefe(caminho, postais):
    pares = set()
    nomeadas = set()
    total = 0
    with ZipFile(caminho) as arquivo:
        info = arquivo.getinfo(CSV_IBGE)
        if info.file_size > 64 * 1024 * 1024:
            raise ValueError('O CSV excede o tamanho esperado para Morrinhos (GO).')
        with arquivo.open(info) as entrada, TextIOWrapper(entrada, encoding='utf-8-sig', newline='') as texto:
            csv_ibge = csv.DictReader(texto, delimiter=';')
            if not CAMPOS_IBGE <= set(csv_ibge.fieldnames or ()):
                raise ValueError('O CSV não tem as colunas esperadas do CNEFE 2022.')
            for linha in csv_ibge:
                if linha['COD_MUNICIPIO'] != '5213806':
                    raise ValueError('O CSV contém linhas fora de Morrinhos (GO).')
                total += 1
                tipo, titulo, nome, local = (linha[ch] for ch in ('NOM_TIPO_SEGLOGR', 'NOM_TITULO_SEGLOGR',
                                                                  'NOM_SEGLOGR', 'DSC_LOCALIDADE'))
                if not chave(nome) or not chave(local):
                    continue
                par = (chave(' '.join(filter(None, (tipo, titulo, nome)))), chave(local))
                pares.add(par)
                if chave(tipo) in TIPOS_VIA and not SEM_NOME.search(chave(nome)):
                    nomeadas.add(par)
    pares_postais = {(linha['nome_chave'], chave(linha['bairro_original'])) for linha in postais}
    nomes_postais = {nome for nome, _ in pares_postais}
    por_local = defaultdict(Counter)
    for nome, local in nomeadas:
        chave_resultado = ('nome_e_local' if (nome, local) in pares_postais else
                           'nome_em_outra_localidade' if nome in nomes_postais else 'sem_nome_exato')
        por_local[local][chave_resultado] += 1
    return {'municipio_ibge': '5213806', 'linhas_lidas': total, 'pares_brutos': len(pares),
            'pares_exatos_brutos': len(pares & pares_postais), 'pares_de_vias_nomeadas': len(nomeadas),
            'pares_exatos_de_vias_nomeadas': len(nomeadas & pares_postais),
            'por_localidade': [{'localidade_normalizada': local, **por_local[local]} for local in sorted(por_local)]}


def main():
    parser = argparse.ArgumentParser(description='Mede lacunas de pesquisa do acervo de Morrinhos (GO).')
    parser.add_argument('--banco', type=Path, default=BANCO)
    parser.add_argument('--cnefe-zip', type=Path, help='Compare com o ZIP municipal CNEFE 2022 do IBGE.')
    args = parser.parse_args()
    try:
        with closing(abrir_banco(args.banco)) as db:
            resumo, postais = cobertura(db)
        if args.cnefe_zip:
            resumo['cnefe_2022'] = cruzar_cnefe(args.cnefe_zip, postais)
    except (OSError, sqlite3.Error, KeyError, BadZipFile, ValueError) as erro:
        parser.exit(1, f'Auditoria indisponível: {erro}\n')
    print(json.dumps(resumo, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
