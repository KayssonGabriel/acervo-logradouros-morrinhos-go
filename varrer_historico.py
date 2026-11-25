import argparse
from collections import Counter, defaultdict
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import subprocess
from zipfile import BadZipFile

from acervo import BANCO, RAIZ, abrir_banco
from auditar_acervo import SEM_NOME, TIPOS_VIA, ler_cnefe, variantes_cnefe
from busca import chave, expandir


CATALOGO = RAIZ / 'dados' / 'pesquisa-historica.json'
TITULOS = {'coronel', 'doutor', 'doutora', 'engenheiro', 'padre', 'prefeito',
           'professor', 'professora', 'senador', 'vereador'}


def cadastrar_alvo(alvos, identificador, bairro, nome):
    if chave(nome):
        alvo = alvos.setdefault(identificador, {'bairro': bairro, 'nomes': set(), 'variantes': set(), 'ocorrencias': []})
        alvo['nomes'].add(nome)


def alvos_do_acervo(db):
    alvos = {}
    bairros = dict(db.execute("SELECT trecho_id, bairro FROM consulta_v1 WHERE situacao_postal <> 'cep_geral_historico'"))
    for trecho, nome in db.execute('''
        SELECT trecho_canonico_id, nome_original FROM observacao_postal_v1
        UNION
        SELECT trecho_id, nome_anterior FROM ato_nome WHERE nome_anterior IS NOT NULL
        UNION
        SELECT trecho_id, nome_atribuido FROM ato_nome
    '''):
        if trecho in bairros:
            cadastrar_alvo(alvos, trecho, bairros[trecho], nome)
    return alvos


def incluir_cnefe(alvos, caminho, ano):
    for tipo, titulo, nome, local in ler_cnefe(caminho, ano):
        tipo_normalizado = chave(tipo)
        if tipo_normalizado not in TIPOS_VIA or not chave(nome) or not chave(local) or SEM_NOME.search(chave(nome)):
            continue
        rotulo = ' '.join(filter(None, (tipo, titulo, nome)))
        identificador = f'cnefe:{ano}:{chave(local)}:{chave(rotulo)}'
        cadastrar_alvo(alvos, identificador, local, rotulo)
        alvos[identificador]['variantes'].update(variantes_cnefe(tipo_normalizado, titulo, nome))


def formar_indice(alvos):
    indice = defaultdict(lambda: defaultdict(set))
    for identificador, alvo in alvos.items():
        termos = set()
        for nome in alvo['nomes'] | alvo['variantes']:
            palavras = tuple(expandir(chave(nome)).split())
            if len(palavras) < 2:
                continue
            termos.add(palavras)
            if len(palavras) > 3 and palavras[1] in TITULOS and palavras[2].isalpha():
                termos.add((palavras[0], *palavras[2:]))
            if palavras[0] == 'v' and palavras[1] == 'dpi':
                termos.add(('via', *palavras[1:]))
            if len(palavras) == 2 and palavras[0] == 'go' and palavras[1].isdigit():
                termos.add(('rodovia', *palavras))
        alvo['termos'] = sorted(' '.join(termo) for termo in termos)
        for termo in termos:
            indice[termo[:2]][termo[2:]].add(identificador)
    return indice


def buscar_pagina(indice, pagina):
    palavras = tuple(expandir(chave(pagina)).split())
    achados = set()
    for posicao in range(len(palavras) - 1):
        prefixo = palavras[posicao:posicao + 2]
        inicio = posicao + 2
        candidatos = indice.get(prefixo, {})
        sufixos = [sufixo for sufixo in candidatos if palavras[inicio:inicio + len(sufixo)] == sufixo]
        if sufixos:
            # Um nome maior nesta posição tem precedência sobre seu prefixo.
            sufixo = max(sufixos, key=len)
            termo = ' '.join((*prefixo, *sufixo))
            achados.update((identificador, termo) for identificador in candidatos[sufixo])
    return achados


def extrair_fonte(pasta, fonte):
    caminho = (pasta / fonte['arquivo']).resolve()
    if caminho.parent != pasta or caminho.suffix.lower() != '.pdf':
        raise ValueError('O catálogo deve apontar para um PDF na pasta de fontes.')
    if caminho.stat().st_size > 64 * 1024 * 1024:
        raise ValueError('PDF acima do limite de 64 MiB.')
    if sha256(caminho.read_bytes()).hexdigest() != fonte['sha256']:
        raise ValueError('O PDF difere da edição catalogada (SHA-256).')
    texto = subprocess.run(['pdftotext', '-enc', 'UTF-8', str(caminho), '-'],
                           capture_output=True, check=True, timeout=60).stdout.decode('utf-8')
    paginas = texto.removesuffix('\f').split('\f')
    primeira, ultima = fonte.get('paginas', [1, len(paginas)])
    if not 1 <= primeira <= ultima <= len(paginas):
        raise ValueError('Intervalo de páginas fora do PDF.')
    return [(numero, paginas[numero - 1]) for numero in range(primeira, ultima + 1)]


def varrer(db, catalogo, pasta, censos=()):
    pasta = pasta.resolve()
    alvos = alvos_do_acervo(db)
    total_acervo = len(alvos)
    for ano, caminho in censos:
        incluir_cnefe(alvos, caminho, ano)
    for item in catalogo['ocorrencias_conferidas']:
        identificador = f"historico:{item['id']}"
        cadastrar_alvo(alvos, identificador, item['localidade'], item['nome'])
        if item.get('nome_correspondente'):
            cadastrar_alvo(alvos, identificador, item['localidade'], item['nome_correspondente'])
    indice = formar_indice(alvos)
    fontes = []
    for fonte in catalogo['fontes']:
        resultado = dict(fonte)
        fontes.append(resultado)
        try:
            paginas = extrair_fonte(pasta, fonte)
        except FileNotFoundError:
            resultado['estado'] = 'extrator_indisponivel' if (pasta / fonte['arquivo']).is_file() else 'pdf_ausente'
            continue
        except (OSError, ValueError, subprocess.SubprocessError):
            resultado['estado'] = 'falha_na_extracao_ou_integridade'
            continue
        com_texto = 0
        for pagina, texto in paginas:
            if not chave(texto):
                continue
            com_texto += 1
            for identificador, termo in sorted(buscar_pagina(indice, texto)):
                alvos[identificador]['ocorrencias'].append({'fonte_id': fonte['id'], 'pagina': pagina, 'termo': termo})
        resultado['paginas_com_texto'] = com_texto
        resultado['paginas_sem_texto'] = len(paginas) - com_texto
        resultado['estado'] = 'texto_pesquisado' if com_texto else 'sem_texto_para_pesquisa'
    registros = []
    por_bairro = defaultdict(Counter)
    for identificador, alvo in sorted(alvos.items(), key=lambda item: (chave(item[1]['bairro']) or '', item[0])):
        bairro = alvo['bairro'] or 'Localidade a identificar'
        busca = por_bairro[bairro]
        busca['registros'] += 1
        busca['com_ocorrencia_textual'] += bool(alvo['ocorrencias'])
        busca['sem_termo_pesquisavel'] += not alvo['termos']
        registros.append({'id': identificador, **alvo, 'nomes': sorted(alvo['nomes']),
                          'variantes': sorted(alvo['variantes'])})
    return {'municipio_ibge': '5213806', 'registros_do_acervo': total_acervo,
            'por_bairro': [{'bairro': bairro, **contagem} for bairro, contagem in por_bairro.items()],
            'fontes': fontes, 'ocorrencias_conferidas': catalogo['ocorrencias_conferidas'], 'registros': registros}


def main():
    parser = argparse.ArgumentParser(description='Pesquisa nomes do acervo em fontes históricas locais de Morrinhos (GO).')
    parser.add_argument('--banco', type=Path, default=BANCO)
    parser.add_argument('--pasta-fontes', type=Path, required=True, help='Pasta com os PDFs do catálogo histórico.')
    parser.add_argument('--cnefe-2010-zip', type=Path)
    parser.add_argument('--cnefe-zip', type=Path, help='ZIP municipal de 2022.')
    args = parser.parse_args()
    censos = [(ano, arquivo) for ano, arquivo in ((2010, args.cnefe_2010_zip), (2022, args.cnefe_zip)) if arquivo]
    try:
        catalogo = json.loads(CATALOGO.read_text(encoding='utf-8'))
        with closing(abrir_banco(args.banco)) as db:
            resultado = varrer(db, catalogo, args.pasta_fontes, censos)
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
    except (OSError, sqlite3.Error, BadZipFile, KeyError, ValueError) as erro:
        parser.exit(1, f'Varredura histórica indisponível: {erro}\n')


if __name__ == '__main__':
    main()
