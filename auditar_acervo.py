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
from busca import ABREVIACOES, chave


ARQUIVOS_IBGE = {2010: '52138060500.TXT', 2022: '5213806_MORRINHOS.csv'}
CAMPOS_IBGE = {'COD_MUNICIPIO', 'DSC_LOCALIDADE', 'NOM_TIPO_SEGLOGR', 'NOM_TITULO_SEGLOGR', 'NOM_SEGLOGR'}
SEM_NOME = re.compile(r'\bsem (?:denominacao|nome|numeracao)\b|^(?:s n|sn)$')
TIPOS_VIA = {'rua', 'avenida', 'alameda', 'praca', 'viela', 'travessa', 'acesso', 'beco',
             'passagem', 'estrada', 'rodovia', 'via', 'lateral', 'marginal', 'saida', 'caminho'}


def cobertura(db, *, listar_pistas=False):
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
        resumo['comparacao_listas_integrais'] = comparar_edicoes(
            db, anterior['id'], fonte['id'], listar_pistas=listar_pistas)
    if listar_pistas:
        complementos = db.execute('''SELECT id FROM fonte
            WHERE tipo = 'lista_postal' AND abrangencia = 'complementar' ORDER BY referencia, id''')
        resumo['comparacao_boletins'] = []
        for boletim in complementos:
            comparacao = comparar_edicoes(db, boletim['id'], fonte['id'], listar_pistas=True)
            comparacao.pop('ceps_so_na_atual')  # O boletim tem escopo parcial.
            resumo['comparacao_boletins'].append(comparacao)
    return resumo, linhas


def comparar_edicoes(db, anterior, atual, *, listar_pistas=False):
    def observacoes(fonte):
        por_cep = defaultdict(list)
        for linha in db.execute('''
            SELECT cep, nome_chave, nome_original AS nome, bairro_original AS bairro,
                   trecho_canonico_id, id AS observacao_id, fonte_id, pagina, linha
            FROM observacao_postal_v1 WHERE fonte_id = ? ORDER BY pagina, linha
        ''', (fonte,)):
            por_cep[linha['cep']].append(linha)
        return por_cep

    def rotulos(linhas):
        return {(linha['nome_chave'], chave(linha['bairro'])) for linha in linhas}

    antigos, recentes = observacoes(anterior), observacoes(atual)
    comuns = antigos.keys() & recentes.keys()
    alterados = sorted(cep for cep in comuns if rotulos(antigos[cep]) != rotulos(recentes[cep]))
    resumo = {'anterior': anterior, 'atual': atual, 'ceps_presentes_nas_duas': len(comuns),
              'ceps_so_na_anterior': sorted(antigos.keys() - recentes.keys()),
              'ceps_so_na_atual': sorted(recentes.keys() - antigos.keys()),
              'ceps_com_rotulos_diferentes': len(alterados)}
    if listar_pistas:
        campos = ('nome', 'bairro', 'fonte_id', 'pagina', 'linha', 'observacao_id', 'trecho_canonico_id')
        resumo['pistas'] = [
            {'cep': cep,
             'anterior': [{campo: linha[campo] for campo in campos} for linha in antigos[cep]],
             'atual': [{campo: linha[campo] for campo in campos} for linha in recentes[cep]],
             'vinculo_documentado': {linha['trecho_canonico_id'] for linha in antigos[cep]} ==
                                    {linha['trecho_canonico_id'] for linha in recentes[cep]}}
            for cep in alterados
        ]
    return resumo


def ler_cnefe(caminho, ano):
    with ZipFile(caminho) as arquivo:
        info = arquivo.getinfo(ARQUIVOS_IBGE[ano])
        if info.file_size > 64 * 1024 * 1024:
            raise ValueError('O arquivo excede o tamanho esperado para Morrinhos (GO).')
        with arquivo.open(info) as entrada:
            if ano == 2010:
                for linha in entrada:
                    linha = linha.rstrip(b'\r\n')
                    if len(linha) != 558 or linha[:7] != b'5213806':
                        raise ValueError('Linha fora do leiaute do CNEFE 2010 de Morrinhos (GO).')
                    yield tuple(linha[inicio:fim].decode('ascii').strip() for inicio, fim in
                                ((16, 36), (36, 66), (66, 126), (351, 411)))
                return
            with TextIOWrapper(entrada, encoding='utf-8-sig', newline='') as arquivo_csv:
                csv_ibge = csv.DictReader(arquivo_csv, delimiter=';')
                if not CAMPOS_IBGE <= set(csv_ibge.fieldnames or ()):
                    raise ValueError('O CSV não tem as colunas esperadas do CNEFE 2022.')
                for linha in csv_ibge:
                    if linha['COD_MUNICIPIO'] != '5213806':
                        raise ValueError('O CSV contém linhas fora de Morrinhos (GO).')
                    yield tuple(linha.get(campo) or '' for campo in
                                ('NOM_TIPO_SEGLOGR', 'NOM_TITULO_SEGLOGR', 'NOM_SEGLOGR', 'DSC_LOCALIDADE'))


def cruzar_cnefe(caminho, postais, *, ano=2022, listar_pistas=False):
    pares, nomeadas, variantes = set(), set(), set()
    total = 0
    for tipo, titulo, nome, local in ler_cnefe(caminho, ano):
        total += 1
        nome_chave, local_chave = chave(nome), chave(local)
        if not nome_chave or not local_chave:
            continue
        par = (chave(' '.join(filter(None, (tipo, titulo, nome)))), local_chave)
        pares.add(par)
        tipo_chave = chave(tipo)
        if tipo_chave not in TIPOS_VIA or SEM_NOME.search(nome_chave):
            continue
        nomeadas.add(par)
        if listar_pistas and ' ou ' in nome_chave:
            nomes = nome_chave.split(' ou ')
            nomes[0] = chave(f'{titulo} {nomes[0]}')
            alternativas = []
            for item in nomes:
                prefixo, separador, restante = item.partition(' ')
                tipo_alternativo = ABREVIACOES.get(prefixo, prefixo)
                if separador and tipo_alternativo in TIPOS_VIA:
                    alternativas.append(f'{tipo_alternativo} {restante}')
                else:
                    alternativas.append(f'{tipo_chave} {item}')
            rotulo = ' '.join(filter(None, (tipo, titulo, nome)))
            variantes.add((local_chave, local, rotulo, tuple(alternativas)))
    pares_postais = {(linha['nome_chave'], chave(linha['bairro_original'])) for linha in postais}
    nomes_postais = {nome for nome, _ in pares_postais}
    por_local = defaultdict(Counter)
    pistas = []
    for nome, local in sorted(nomeadas, key=lambda par: (par[1], par[0])):
        chave_resultado = ('nome_e_local' if (nome, local) in pares_postais else
                           'nome_em_outra_localidade' if nome in nomes_postais else 'sem_nome_exato')
        por_local[local][chave_resultado] += 1
        if listar_pistas and chave_resultado != 'nome_e_local':
            pistas.append({'localidade_normalizada': local, 'nome_normalizado': nome, 'comparacao': chave_resultado})
    resumo = {'municipio_ibge': '5213806', 'linhas_lidas': total, 'pares_brutos': len(pares),
              'pares_exatos_brutos': len(pares & pares_postais), 'pares_de_vias_nomeadas': len(nomeadas),
              'pares_exatos_de_vias_nomeadas': len(nomeadas & pares_postais),
              'por_localidade': [{'localidade_normalizada': local, **por_local[local]} for local in sorted(por_local)]}
    if listar_pistas:
        resumo['pistas'] = pistas
        resumo['variantes_explicitas'] = [
            {'localidade_normalizada': local, 'localidade_original': original, 'rotulo_original': rotulo,
             'nomes': list(nomes)} for local, original, rotulo, nomes in sorted(variantes)
        ]
    return resumo


def main():
    parser = argparse.ArgumentParser(description='Mede lacunas de pesquisa do acervo de Morrinhos (GO).')
    parser.add_argument('--banco', type=Path, default=BANCO)
    parser.add_argument('--cnefe-zip', type=Path, help='Compare com o ZIP municipal CNEFE 2022 do IBGE.')
    parser.add_argument('--cnefe-2010-zip', type=Path, help='Compare com o ZIP do CNEFE 2010 de Morrinhos (GO).')
    parser.add_argument('--pistas', action='store_true', help='Liste diferenças postais e pistas censitárias por via.')
    args = parser.parse_args()
    try:
        with closing(abrir_banco(args.banco)) as db:
            resumo, postais = cobertura(db, listar_pistas=args.pistas)
        for ano, caminho in ((2010, args.cnefe_2010_zip), (2022, args.cnefe_zip)):
            if caminho:
                resumo[f'cnefe_{ano}'] = cruzar_cnefe(caminho, postais, ano=ano, listar_pistas=args.pistas)
    except (OSError, sqlite3.Error, KeyError, BadZipFile, ValueError) as erro:
        parser.exit(1, f'Auditoria indisponível: {erro}\n')
    print(json.dumps(resumo, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
