import argparse
from contextlib import closing, contextmanager
import csv
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import tempfile
import unicodedata
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, uuid5

from busca import chave, expandir, interpretar, pontuador, separar_bairro, variantes_bairro


RAIZ = Path(__file__).resolve().parent
BANCO = RAIZ / 'morrinhos.sqlite3'
BASE_INICIAL = RAIZ / 'dados' / 'base-inicial.sqlite3'
CEP = r'[0-9]{5}-?[0-9]{3}'
LINHA_PADRAO = re.compile(rf'\s*(.+?)\s+({CEP})(?:\s+(.+?))?\s*')
LINHA_NUMERADA = re.compile(rf'\s*(\d+)\s{{2,}}(.+?)\s{{2,}}(.+?)\s{{2,}}({CEP})\s*')


def cep_formatado(valor):
    if not re.fullmatch(CEP, valor):
        raise ValueError(f'CEP inválido: {valor}')
    digitos = valor.replace('-', '')
    return f'{digitos[:5]}-{digitos[5:]}'


def abrir_banco(caminho, escrita=False):
    caminho = caminho.absolute()
    if caminho == BANCO and not caminho.exists() and not caminho.is_symlink() and BASE_INICIAL.is_file():
        try:
            with publicar_arquivo(caminho) as temporario:
                shutil.copyfile(BASE_INICIAL, temporario)
        except FileExistsError:
            # Outra instância terminou de criar a base local primeiro.
            if not caminho.is_file():
                raise
    caminho = caminho.resolve()
    if escrita and caminho == BASE_INICIAL.resolve():
        raise ValueError('A base inicial é somente leitura. Use a cópia local para trabalhar.')
    modo = 'rwc' if escrita else 'ro'
    db = sqlite3.connect(f'{caminho.as_uri()}?mode={modo}', uri=True)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    versao = db.execute('PRAGMA user_version').fetchone()[0]
    try:
        if escrita and versao == 0:
            db.executescript((RAIZ / 'dados/esquema.sql').read_text(encoding='utf-8'))
            versao = 1
        if escrita and versao == 1:
            db.executescript((RAIZ / 'dados/migracao-002.sql').read_text(encoding='utf-8'))
            versao = 2
        if escrita and versao == 2:
            db.executescript((RAIZ / 'dados/migracao-003.sql').read_text(encoding='utf-8'))
            versao = 3
        if escrita and versao == 3:
            db.executescript((RAIZ / 'dados/migracao-004.sql').read_text(encoding='utf-8'))
            versao = 4
        if versao != 4 and not (versao in (2, 3) and not escrita):
            raise ValueError(f'Versão de esquema não suportada para consulta: {versao}. Execute importar para migrar.')
    except (sqlite3.Error, OSError, ValueError):
        db.close()
        raise
    return db


def dados_fonte(fonte, tipo):
    caminho = fonte.get('arquivo')
    conteudo = None
    if caminho:
        arquivo = (RAIZ / caminho).resolve()
        if not arquivo.is_relative_to(RAIZ):
            raise ValueError(f"A fonte {fonte['id']} deve estar dentro da pasta do acervo.")
        if arquivo.suffix.lower() != '.pdf':
            raise ValueError(f"A fonte {fonte['id']} deve apontar para um PDF.")
        conteudo = arquivo.read_bytes()
        if not conteudo.startswith(b'%PDF-'):
            raise ValueError(f"O arquivo da fonte {fonte['id']} não tem cabeçalho PDF.")
    elif tipo != 'comunicado':
        raise ValueError(f"Campo arquivo obrigatório para a fonte {fonte['id']}.")
    digest = hashlib.sha256(conteudo).hexdigest() if conteudo else None
    abrangencia = fonte.get('abrangencia', 'integral') if tipo == 'lista_postal' else None
    campos = (tipo, fonte['referencia'], caminho, fonte['url'], digest,
              fonte.get('prioridade', 0), fonte.get('nota'), abrangencia)
    return campos, conteudo


def fonte_ja_registrada(db, fonte_id, campos):
    existente = db.execute('''
        SELECT tipo, referencia, arquivo, url, sha256, prioridade, nota, abrangencia FROM fonte WHERE id = ?
    ''', (fonte_id,)).fetchone()
    if existente is not None and tuple(existente) != campos:
        raise ValueError(f'Mantenha a fonte original {fonte_id}. Cadastre outra edição com um novo ID.')
    return existente is not None


def registrar_fonte(db, fonte_id, campos):
    if fonte_ja_registrada(db, fonte_id, campos):
        return False
    db.execute('''
        INSERT INTO fonte (id, tipo, referencia, arquivo, url, sha256, prioridade, nota, abrangencia)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (fonte_id, *campos))
    return True


def garantir_trecho(db, tipo, identificador, bairro=None):
    trecho_id = str(uuid5(NAMESPACE_URL, f'br.go.morrinhos/acervo/{tipo}/{identificador}'))
    bairro_id = None
    if bairro:
        bairro_chave = chave(bairro)
        db.execute('INSERT INTO bairro (nome, chave) VALUES (?, ?) ON CONFLICT(chave) DO NOTHING',
                   (bairro, bairro_chave))
        bairro_id = db.execute('SELECT id FROM bairro WHERE chave = ?', (bairro_chave,)).fetchone()[0]
    db.execute('INSERT INTO trecho (id, bairro_id, tipo) VALUES (?, ?, ?) ON CONFLICT(id) DO NOTHING',
               (trecho_id, bairro_id, tipo))
    return trecho_id


def ler_lista(fonte, conteudo):
    pdftotext = shutil.which('pdftotext')
    if pdftotext is None:
        raise FileNotFoundError('pdftotext não foi encontrado no PATH.')
    executavel = Path(pdftotext).resolve()
    if executavel.is_relative_to(RAIZ):
        raise ValueError('Use a instalação do pdftotext fora da pasta do acervo.')
    resultado = subprocess.run(
        [str(executavel), '-enc', 'UTF-8', '-layout', '-', '-'], input=conteudo,
        capture_output=True, check=True, timeout=45,
    )
    registros = []
    for pagina, texto in enumerate(resultado.stdout.decode('utf-8').split('\f'), start=1):
        for linha, conteudo in enumerate(texto.splitlines(), start=1):
            if fonte.get('formato') == 'numerado':
                dados = LINHA_NUMERADA.fullmatch(conteudo)
                if dados:
                    _, nome, bairro, cep = dados.groups()
                    registros.append((pagina, linha, nome, bairro, cep))
            else:
                dados = LINHA_PADRAO.fullmatch(conteudo)
                if dados:
                    nome, cep, bairro = dados.groups()
                    registros.append((pagina, linha, nome, bairro, cep))
    if len(registros) != fonte['linhas']:
        raise ValueError(f"{fonte['arquivo']}: esperadas {fonte['linhas']} linhas, lidas {len(registros)}")
    return registros


def preparar_lista(db, fonte):
    campos, conteudo = dados_fonte(fonte, 'lista_postal')
    if fonte_ja_registrada(db, fonte['id'], campos):
        return campos, None
    return campos, ler_lista(fonte, conteudo)


def importar_lista(db, fonte, preparada=None):
    campos, registros = preparada if preparada is not None else preparar_lista(db, fonte)
    if not registrar_fonte(db, fonte['id'], campos):
        total = db.execute('SELECT count(*) FROM observacao_postal WHERE fonte_id = ?', (fonte['id'],)).fetchone()[0]
        if total != fonte['linhas']:
            raise ValueError(f"Quantidade já importada difere do catálogo para {fonte['id']}.")
        return
    if registros is None:
        raise ValueError(f"A fonte {fonte['id']} mudou durante a preparação. Reexecute a importação.")
    for pagina, linha, nome, bairro, cep_original in registros:
        cep = cep_formatado(cep_original)
        nome_chave = chave(nome)
        bairro_chave = chave(bairro) if bairro else ''
        trecho = garantir_trecho(db, 'registro_postal', f'{bairro_chave}/{nome_chave}/{cep}', bairro)
        db.execute('''
            INSERT INTO observacao_postal (trecho_id, fonte_id, pagina, linha, nome_original,
                nome_chave, bairro_original, cep_original, cep)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (trecho, fonte['id'], pagina, linha, nome, nome_chave, bairro, cep_original, cep))


def encontrar_trecho_postal(db, vinculo):
    resultado = db.execute('''
        SELECT DISTINCT t.id FROM trecho t JOIN bairro b ON b.id = t.bairro_id
        JOIN observacao_postal o ON o.trecho_id = t.id
        WHERE b.chave = ? AND o.nome_chave = ? AND o.cep = ?
    ''', (chave(vinculo['bairro']), chave(vinculo['nome']), cep_formatado(vinculo['cep']))).fetchall()
    if len(resultado) != 1:
        raise ValueError(f'Vínculo postal sem correspondência única: {vinculo}')
    return resultado[0]['id']


def importar_ato(db, ato, campos=None):
    if campos is None:
        campos, _ = dados_fonte(ato, 'lei_municipal')
    registrar_fonte(db, ato['id'], campos)
    ato_id = ato.get('registro', ato['id'])
    vinculo = ato.get('vinculo_postal')
    trecho_ato = ato.get('trecho_ato')
    if vinculo:
        trecho = encontrar_trecho_postal(db, vinculo)
    elif trecho_ato:
        anterior_registrado = db.execute('SELECT trecho_id FROM ato_nome WHERE id = ?', (trecho_ato,)).fetchone()
        if anterior_registrado is None:
            raise ValueError(f'Ato de referência ainda não registrado: {trecho_ato}')
        trecho = anterior_registrado['trecho_id']
    else:
        trecho = garantir_trecho(db, 'trecho_de_lei', ato_id, ato['bairro'])
    if db.execute('SELECT 1 FROM equivalencia_trecho WHERE anterior_id = ?', (trecho,)).fetchone():
        raise ValueError(f'Use o trecho principal como referência no ato {ato_id}.')
    anterior = ato.get('anterior')
    db.execute('''
        INSERT INTO ato_nome (id, trecho_id, fonte_id, numero, artigo, pagina, bairro_no_ato,
            trecho_no_ato, nome_anterior, anterior_chave, nome_atribuido, atribuido_chave,
            data_publicacao, vigencia_desde, nota)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET trecho_id = excluded.trecho_id, fonte_id = excluded.fonte_id,
            numero = excluded.numero, artigo = excluded.artigo, pagina = excluded.pagina,
            bairro_no_ato = excluded.bairro_no_ato, trecho_no_ato = excluded.trecho_no_ato,
            nome_anterior = excluded.nome_anterior, anterior_chave = excluded.anterior_chave,
            nome_atribuido = excluded.nome_atribuido, atribuido_chave = excluded.atribuido_chave,
            data_publicacao = excluded.data_publicacao, vigencia_desde = excluded.vigencia_desde,
            nota = excluded.nota
    ''', (ato_id, trecho, ato['id'], ato['numero'], ato['artigo'], ato['pagina'], ato['bairro'],
          ato.get('trecho'), anterior, chave(anterior) if anterior else None, ato['atribuido'],
          chave(ato['atribuido']), ato.get('data_publicacao'), ato.get('vigencia_desde'), ato.get('nota')))
    vinculados = ato.get('registros_postais_anteriores', []) + ato.get('registros_postais_vinculados', [])
    anteriores = {encontrar_trecho_postal(db, registro) for registro in vinculados}
    anteriores_salvos = db.execute('SELECT anterior_id, principal_id FROM equivalencia_trecho WHERE ato_id = ?',
                                   (ato_id,)).fetchall()
    for vinculo_salvo in anteriores_salvos:
        if vinculo_salvo['anterior_id'] not in anteriores or vinculo_salvo['principal_id'] != trecho:
            db.execute('DELETE FROM equivalencia_trecho WHERE anterior_id = ? AND ato_id = ?',
                       (vinculo_salvo['anterior_id'], ato_id))
    for trecho_anterior in sorted(anteriores):
        vinculo_existente = db.execute('''
            SELECT principal_id FROM equivalencia_trecho WHERE anterior_id = ? OR principal_id = ?
        ''', (trecho_anterior, trecho_anterior)).fetchall()
        if any(linha['principal_id'] != trecho for linha in vinculo_existente):
            raise ValueError(f'Trecho com equivalência já vinculada a outro registro: {trecho_anterior}')
        db.execute('''
            INSERT INTO equivalencia_trecho (anterior_id, principal_id, ato_id)
            VALUES (?, ?, ?) ON CONFLICT(anterior_id) DO NOTHING
        ''', (trecho_anterior, trecho, ato_id))


def importar_nomes_historicos(db, catalogo):
    fontes = {fonte['id']: fonte for fonte in catalogo['fontes']}
    registros = []
    for nome in catalogo['ocorrencias_conferidas']:
        vinculo = nome.get('vinculo_postal')
        if not vinculo:
            continue
        if chave(nome['nome_correspondente']) != chave(vinculo['nome']):
            raise ValueError(f"Nome do vínculo postal difere da correspondência histórica: {nome['id']}.")
        fonte = fontes[nome['fonte_id']]
        trecho = encontrar_trecho_postal(db, vinculo)
        registros.append((nome['id'], trecho, nome['nome'], chave(nome['nome']), nome.get('ano'),
                          fonte['id'], fonte['titulo'], fonte['url'], nome['pagina'],
                          nome['pagina_correspondencia'], nome['nota_vinculo']))
    db.execute('DELETE FROM nome_historico')
    db.executemany('''INSERT INTO nome_historico (id, trecho_id, nome, nome_chave, ano, fonte_id, fonte, url,
                                                  pagina, pagina_correspondencia, nota)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', registros)


def importar(db):
    dados = json.loads((RAIZ / 'dados/fontes.json').read_text(encoding='utf-8'))
    historico = json.loads((RAIZ / 'dados/pesquisa-historica.json').read_text(encoding='utf-8'))
    listas = [(fonte, preparar_lista(db, fonte)) for fonte in dados['listas']]
    atos_preparados = [(ato, dados_fonte(ato, 'lei_municipal')[0]) for ato in dados['atos']]
    geral = dados['cep_geral']
    campos_geral, _ = dados_fonte(geral, 'comunicado')
    db.execute('BEGIN IMMEDIATE')
    with db:
        for fonte, preparacao in listas:
            importar_lista(db, fonte, preparacao)
        for ato, campos in atos_preparados:
            importar_ato(db, ato, campos)
        importar_nomes_historicos(db, historico)
        registrar_fonte(db, geral['id'], campos_geral)
        trecho = garantir_trecho(db, 'cep_geral_historico', geral['cep'])
        db.execute('''
            INSERT INTO observacao_postal (trecho_id, fonte_id, pagina, linha, nome_original,
                nome_chave, cep_original, cep, fim_anunciado)
            VALUES (?, ?, 1, 1, 'CEP geral de Morrinhos', 'cep geral de morrinhos', ?, ?, ?)
            ON CONFLICT(fonte_id, pagina, linha) DO NOTHING
        ''', (trecho, geral['id'], geral['cep'], geral['cep'], geral['fim_anunciado']))
    return {'observacoes_postais': db.execute('SELECT count(*) FROM observacao_postal').fetchone()[0],
            'atos_documentados': db.execute('SELECT count(*) FROM ato_nome').fetchone()[0],
            'nomes_historicos_vinculados': db.execute('SELECT count(*) FROM nome_historico').fetchone()[0]}


def atos(db, trecho_id):
    return [dict(linha) for linha in db.execute('''
        SELECT a.fonte_id, a.numero, a.artigo, a.pagina, f.referencia AS data_ato,
            a.bairro_no_ato, a.trecho_no_ato, a.nome_anterior, a.nome_atribuido,
            a.data_publicacao, a.vigencia_desde, f.url, f.arquivo, a.nota
        FROM ato_nome a JOIN fonte f ON f.id = a.fonte_id
        WHERE a.trecho_id = ? ORDER BY f.referencia, a.id
    ''', (trecho_id,))]


def registrar_mudanca(db, dados):
    limites = {'trecho_id': 36, 'nome_anterior': 120, 'nome_novo': 120, 'vigencia_desde': 10,
               'situacao_cep': 16, 'cep_anterior': 9, 'cep_novo': 9, 'fonte': 500, 'url_fonte': 1500}
    if not isinstance(dados, dict) or dados.keys() - limites.keys():
        raise ValueError('Campos de cadastro inválidos.')
    registro = {}
    for campo, limite in limites.items():
        valor = dados.get(campo, '')
        if not isinstance(valor, str) or len(valor) > limite or any(ord(c) < 32 for c in valor):
            raise ValueError(f'Valor inválido para {campo.replace("_", " ")}.')
        registro[campo] = valor.strip() or None

    trecho_id, anterior, novo, vigencia, situacao, cep_anterior, cep_novo, fonte, url = registro.values()
    if not trecho_id or not fonte or situacao not in ('alterado', 'mantido', 'desconhecido'):
        raise ValueError('Selecione o trecho, a situação do CEP e informe a referência da fonte.')
    if (anterior and not novo) or any(nome and not chave(nome) for nome in (anterior, novo)):
        raise ValueError('Informe o novo nome ou deixe os nomes vazios para uma mudança apenas de CEP.')
    if (not novo or anterior == novo) and situacao != 'alterado':
        raise ValueError('Informe uma alteração de nome ou de CEP.')
    if vigencia:
        try:
            if date.fromisoformat(vigencia).isoformat() != vigencia:
                raise ValueError()
        except ValueError:
            raise ValueError('Informe uma data de vigência válida.') from None
    if url:
        partes = urlsplit(url)
        if partes.scheme != 'https' or not partes.hostname or partes.username is not None or partes.password is not None:
            raise ValueError('Informe um link HTTPS público para a fonte.')
    cep_anterior = cep_formatado(cep_anterior) if cep_anterior else None
    cep_novo = cep_formatado(cep_novo) if cep_novo else None
    if situacao == 'alterado' and (not cep_novo or cep_novo == cep_anterior):
        raise ValueError('Informe um novo CEP diferente do anterior.')
    if situacao == 'mantido':
        if not cep_anterior or cep_novo and cep_novo != cep_anterior:
            raise ValueError('Informe o CEP que permaneceu igual.')
        cep_novo = cep_anterior
    if situacao == 'desconhecido' and cep_novo:
        raise ValueError('Deixe o novo CEP vazio quando ele ainda está a confirmar.')

    db.execute('BEGIN IMMEDIATE')
    with db:
        trecho = db.execute('''SELECT situacao_postal FROM consulta_v1 WHERE trecho_id = ?''', (trecho_id,)).fetchone()
        if trecho is None or trecho['situacao_postal'] == 'cep_geral_historico':
            raise ValueError('Selecione um trecho de logradouro disponível na consulta.')
        campos = (trecho_id, anterior, chave(anterior), novo, chave(novo), vigencia,
                  situacao, cep_anterior, cep_novo, fonte, url)
        identificador = str(uuid5(NAMESPACE_URL, 'br.go.morrinhos/acervo/mudanca/' + json.dumps(campos)))
        cursor = db.execute('''
            INSERT INTO mudanca_local (id, trecho_id, nome_anterior, anterior_chave, nome_novo, novo_chave,
                                       vigencia_desde, situacao_cep, cep_anterior, cep_novo, fonte, url_fonte)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO NOTHING
        ''', (identificador, *campos))
        return {'id': identificador, 'criado': cursor.rowcount == 1}


def localizar(db, nome, bairro, cep, *, variantes=False):
    bairros = variantes_bairro(bairro)
    versao = db.execute('PRAGMA user_version').fetchone()[0]
    nomes = 'nomes_acervo_v1' if versao >= 3 else '''(
        SELECT trecho_canonico_id AS trecho_id, nome_chave FROM observacao_postal_v1
        UNION ALL SELECT trecho_id, anterior_chave FROM ato_nome WHERE anterior_chave IS NOT NULL
        UNION ALL SELECT trecho_id, atribuido_chave FROM ato_nome
    )'''
    if versao >= 4:
        nomes = 'nomes_acervo_v2'
    ceps = 'ceps_acervo_v1' if versao >= 3 else '(SELECT trecho_canonico_id AS trecho_id, cep FROM observacao_postal_v1)'
    if not nome:
        candidatos = f'SELECT DISTINCT trecho_id, 4 AS peso FROM {ceps} WHERE cep = ?'
        parametros = [cep]
    elif variantes:
        db.create_function('pontuar', 1, pontuador(nome), deterministic=True)
        candidatos = f'''
            SELECT trecho_id, max(peso) AS peso FROM (
                SELECT trecho_id, pontuar(nome_chave) AS peso FROM {nomes}
            ) WHERE peso > 0 GROUP BY trecho_id
        '''
        parametros = []
    else:
        parametros = [f'% {nome} %', f'% {expandir(nome)} %']
        candidatos = f'''
            SELECT DISTINCT trecho_id, 4 AS peso FROM {nomes}
                WHERE (' ' || nome_chave || ' ') LIKE ? OR (' ' || nome_chave || ' ') LIKE ?
        '''
    filtros = []
    if nome and cep:
        filtros.append(f'c.trecho_id IN (SELECT trecho_id FROM {ceps} WHERE cep = ?)')
        parametros.append(cep)
    if bairros:
        marcadores = ', '.join('?' for _ in bairros)
        filtros.append(f'''c.trecho_id IN (
            SELECT t.id FROM trecho t JOIN bairro b ON b.id = t.bairro_id WHERE b.chave IN ({marcadores})
            UNION
            SELECT trecho_id FROM ato_nome WHERE normalizar(bairro_no_ato) IN ({marcadores})
            UNION
            SELECT trecho_canonico_id FROM observacao_postal_v1 WHERE normalizar(bairro_original) IN ({marcadores})
        )''')
        parametros.extend(bairros * 3)
    db.create_function('normalizar', 1, chave, deterministic=True)
    restricoes = 'WHERE ' + ' AND '.join(filtros) if filtros else ''
    return db.execute(f'''
        SELECT c.*, candidatos.peso FROM consulta_v1 c
        JOIN ({candidatos}) candidatos
            ON candidatos.trecho_id = c.trecho_id
        {restricoes}
        ORDER BY candidatos.peso DESC, referencia_postal DESC, bairro, nome_postal_publicado, trecho_id
    ''', parametros).fetchall()


def consultar(db, termo, bairro, *, limite=None, deslocamento=0):
    entrada = interpretar(termo, bairro)
    if entrada.conflito:
        registros = []
    else:
        if not entrada.nome and not entrada.cep:
            raise ValueError('Informe um nome ou CEP para pesquisar.')
        nome, bairro = entrada.nome, entrada.bairro
        registros = localizar(db, nome, bairro, entrada.cep)
        if not registros and nome:
            nomes_bairro = [linha[0] for linha in db.execute('SELECT nome FROM bairro UNION SELECT bairro_no_ato FROM ato_nome')]
            if entrada.cep and not bairro and any(nome in variantes_bairro(item) for item in nomes_bairro):
                registros = localizar(db, '', nome, entrada.cep)
            nome_curto, sufixo = separar_bairro(nome, nomes_bairro)
            if not registros and sufixo and (not bairro or set(variantes_bairro(bairro)).intersection(variantes_bairro(sufixo))):
                nome, bairro = nome_curto, bairro or sufixo
                registros = localizar(db, nome, bairro, entrada.cep)
            if not registros:
                registros = localizar(db, nome, bairro, entrada.cep, variantes=True)
                if registros:
                    registros = [linha for linha in registros if linha['peso'] == registros[0]['peso']]
    nomes_criterio = {1: 'aproximada', 2: 'prefixo', 3: 'termos', 4: 'texto' if entrada.nome else 'cep'}
    criterio = nomes_criterio[registros[0]['peso']] if registros else 'nenhuma'
    total = len(registros)
    if limite is not None:
        registros = registros[deslocamento:deslocamento + limite]
    resultados = []
    versao = db.execute('PRAGMA user_version').fetchone()[0]
    for linha in registros:
        resultado = dict(linha)
        resultado.pop('bairro_chave')
        resultado.pop('peso')
        resultado['divergencia_postal'] = bool(resultado['divergencia_postal'])
        resultado['historico_nomes'] = atos(db, linha['trecho_id'])
        resultado['nomes_historicos'] = [dict(nome) for nome in db.execute('''
            SELECT nome, ano, fonte_id, fonte, url, pagina, pagina_correspondencia, nota
            FROM nome_historico_v1 WHERE trecho_canonico_id = ? ORDER BY ano, nome, id
        ''', (linha['trecho_id'],))] if versao >= 4 else []
        resultado['mudancas_cadastradas'] = [dict(mudanca) for mudanca in db.execute('''
            SELECT id, nome_anterior, nome_novo, vigencia_desde, situacao_cep, cep_anterior, cep_novo,
                   fonte, url_fonte, registrado_em
            FROM mudanca_local_v1 WHERE trecho_canonico_id = ?
            ORDER BY vigencia_desde IS NULL, vigencia_desde DESC, registrado_em DESC, id
        ''', (linha['trecho_id'],))] if versao >= 3 else []
        resultado['observacoes_postais'] = [dict(o) for o in db.execute('''
            SELECT o.id, o.fonte_id, f.referencia, o.pagina, o.linha, o.nome_original,
                o.bairro_original, o.cep_original, o.cep, f.url, f.arquivo
            FROM observacao_postal o JOIN fonte f ON f.id = o.fonte_id
            WHERE o.trecho_id IN (SELECT ? UNION ALL SELECT anterior_id FROM equivalencia_trecho WHERE principal_id = ?)
            ORDER BY f.referencia DESC, f.prioridade DESC, f.id, o.pagina, o.linha
        ''', (linha['trecho_id'], linha['trecho_id']))]
        resultados.append(resultado)
    resposta = {'versao': 1, 'criterio': criterio, 'cep_geral_informado': entrada.cep_geral,
                'conflito_entrada': entrada.conflito, 'resultados': resultados}
    if limite is not None:
        resposta['total'] = total
    return resposta


@contextmanager
def publicar_arquivo(destino):
    if destino.exists():
        raise FileExistsError(f'O destino já existe: {destino}')
    with tempfile.NamedTemporaryFile(dir=destino.parent, prefix=f'.{destino.name}.', delete=False) as reserva:
        temporario = Path(reserva.name)
    try:
        yield temporario
        if os.name == 'nt':
            temporario.rename(destino)
        else:
            os.link(temporario, destino)
    finally:
        temporario.unlink(missing_ok=True)


def texto_excel(valor):
    if isinstance(valor, str) and (
        valor.startswith(('\t', '\r', '\n')) or
        unicodedata.normalize('NFKC', valor.lstrip()).startswith(('=', '+', '-', '@'))
    ):
        return "'" + valor
    return valor


def exportar(db, destino):
    campos = ('trecho_id', 'municipio', 'uf', 'bairro', 'trecho_documentado', 'nome_municipal_documentado',
              'nome_postal_publicado', 'cep_publicado', 'situacao_historico', 'situacao_postal', 'referencia_postal',
              'url_fonte_postal', 'pagina_fonte_postal', 'url_fonte_municipal', 'pagina_fonte_municipal',
              'abrangencia_fonte_postal', 'divergencia_postal', 'conferencia_correios',
              'conferido_em', 'nomes_anteriores')
    registros = db.execute('SELECT * FROM consulta_v1 ORDER BY bairro, nome_postal_publicado, trecho_id')
    with publicar_arquivo(destino) as temporario, temporario.open('w', newline='', encoding='utf-8-sig') as arquivo:
        csv_writer = csv.DictWriter(arquivo, fieldnames=campos, delimiter=';', extrasaction='ignore')
        csv_writer.writeheader()
        total = 0
        for registro in registros:
            linha = dict(registro)
            nomes = {ato['nome_anterior'] for ato in atos(db, linha['trecho_id']) if ato['nome_anterior']}
            linha['nomes_anteriores'] = ' | '.join(sorted(nomes))
            csv_writer.writerow({campo: texto_excel(linha[campo]) for campo in campos})
            total += 1
    return {'arquivo': str(destino.resolve()), 'linhas': total}


def backup(db, destino):
    with publicar_arquivo(destino) as temporario, closing(sqlite3.connect(temporario)) as copia:
        db.backup(copia)
        if [linha[0] for linha in copia.execute('PRAGMA integrity_check')] != ['ok']:
            raise ValueError('A cópia de segurança não passou na checagem de integridade.')
        if copia.execute('PRAGMA foreign_key_check').fetchone() is not None:
            raise ValueError('A cópia de segurança contém referências inválidas.')
    return {'arquivo': str(destino.resolve()), 'integridade': 'ok'}


def gerar_base_inicial(destino):
    with tempfile.TemporaryDirectory() as pasta:
        with closing(abrir_banco(Path(pasta) / 'fontes-publicas.sqlite3', escrita=True)) as db:
            contagem = importar(db)
            copia = backup(db, destino)
    return {**copia, **contagem}


def registrar_conferencia(db, args):
    dia = date.fromisoformat(args.data).isoformat()
    if not args.responsavel.strip() or not args.evidencia.strip():
        raise ValueError('Informe o responsável e a evidência da conferência.')
    with db:
        resultado = db.execute('''
            INSERT INTO conferencia_correios
                (observacao_id, conferido_em, responsavel, resultado, endereco_retornado, evidencia)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (args.observacao_id, dia, args.responsavel, args.resultado, args.endereco, args.evidencia))
    return {'conferencia_id': resultado.lastrowid}


def main():
    cli = argparse.ArgumentParser(description='Acervo de logradouros e CEPs de Morrinhos (GO)')
    cli.add_argument('--banco', type=Path, default=BANCO)
    comandos = cli.add_subparsers(dest='comando', required=True)
    comandos.add_parser('importar', help='Importa as fontes catalogadas')
    base_inicial = comandos.add_parser('gerar-base-inicial', help='Gera um banco novo apenas com as fontes públicas')
    base_inicial.add_argument('destino', type=Path)
    busca = comandos.add_parser('consultar', help='Pesquisa um nome ou CEP e devolve JSON')
    busca.add_argument('termo')
    busca.add_argument('--bairro')
    exportacao = comandos.add_parser('exportar', help='Grava um novo CSV para Excel')
    exportacao.add_argument('destino', type=Path)
    copia = comandos.add_parser('backup', help='Cria uma cópia SQLite consistente e verificada')
    copia.add_argument('destino', type=Path)
    conferencia = comandos.add_parser('registrar-conferencia', help='Registra uma consulta já feita nos Correios')
    conferencia.add_argument('observacao_id', type=int)
    conferencia.add_argument('--data', required=True)
    conferencia.add_argument('--responsavel', required=True)
    conferencia.add_argument('--resultado', required=True, choices=('confirmado', 'divergente', 'nao_localizado'))
    conferencia.add_argument('--endereco')
    conferencia.add_argument('--evidencia', required=True)
    args = cli.parse_args()
    try:
        if args.comando == 'gerar-base-inicial':
            print(json.dumps(gerar_base_inicial(args.destino), ensure_ascii=False, indent=2))
            return
        db = abrir_banco(args.banco, escrita=args.comando in ('importar', 'registrar-conferencia'))
        try:
            if args.comando == 'importar':
                resultado = importar(db)
            elif args.comando == 'consultar':
                resultado = consultar(db, args.termo, args.bairro)
            elif args.comando == 'exportar':
                resultado = exportar(db, args.destino)
            elif args.comando == 'backup':
                resultado = backup(db, args.destino)
            else:
                resultado = registrar_conferencia(db, args)
        finally:
            db.close()
    except (OSError, sqlite3.Error, ValueError, subprocess.SubprocessError) as erro:
        cli.exit(1, f'Erro: {erro}\n')
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
