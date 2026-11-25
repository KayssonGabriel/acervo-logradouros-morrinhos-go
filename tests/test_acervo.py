from contextlib import closing
import csv
import json
from pathlib import Path
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import acervo
import auditar_acervo
import varrer_historico


ROOT = Path(__file__).resolve().parents[1]


class TestAcervo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pasta = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.pasta.cleanup)
        cls.banco = Path(cls.pasta.name) / 'teste.sqlite3'
        cls.importar = cls.cli('importar')

    @classmethod
    def cli(cls, *args, banco=None):
        return subprocess.run(
            [sys.executable, '-X', 'utf8', str(ROOT / 'acervo.py'), '--banco', str(banco or cls.banco), *args],
            cwd=ROOT, capture_output=True, text=True, encoding='utf-8',
        )

    def consultar(self, *args, banco=None):
        result = self.cli('consultar', *args, banco=banco)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)['resultados']

    def test_importa_todas_as_linhas_sem_duplicar_ao_repetir(self):
        self.assertEqual(self.importar.returncode, 0, self.importar.stderr)
        repeticao = self.cli('importar')
        self.assertEqual(repeticao.returncode, 0, repeticao.stderr)
        with closing(sqlite3.connect(self.banco)) as db:
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
            contagem = dict(db.execute('SELECT fonte_id, count(*) FROM observacao_postal GROUP BY fonte_id'))
            self.assertEqual(contagem['lista-2025-12-bairro'], 1021)
            self.assertEqual(contagem['lista-2025-12-alfabetica'], 1021)
            self.assertEqual(contagem['lista-2025-10'], 35)
            self.assertEqual(contagem['lista-2024-11'], 970)
            self.assertEqual(contagem['lista-2025-01'], 970)
            self.assertEqual(contagem['lista-2025-01-bairro'], 970)
            self.assertEqual(db.execute('SELECT count(*) FROM ato_nome').fetchone()[0], 106)

    def test_nome_anterior_documentado_encontra_cep_por_bairro(self):
        resultado, = self.consultar('Rua 03', '--bairro', 'Jardim América')
        self.assertEqual(resultado['nome_municipal_documentado'], 'Rua Juvercina Cipriana da Silva')
        self.assertEqual(resultado['cep_publicado'], '75650-281')
        self.assertEqual(resultado['conferencia_correios'], 'pendente')
        self.assertEqual(resultado['historico_nomes'][0]['fonte_id'], 'lei-3119-2015')

    def test_nome_historico_textual_encontra_o_trecho_sem_virar_ato_ou_conferencia(self):
        trecho, = self.consultar('Rua do Comércio')
        self.assertEqual((trecho['bairro'], trecho['cep_publicado']), ('Centro', '75650-114'))
        self.assertEqual(trecho['nome_postal_publicado'], 'Rua Barão do Rio Branco')
        registro, = trecho['nomes_historicos']
        self.assertEqual((registro['ano'], registro['pagina'], registro['pagina_correspondencia']), (1896, 50, 42))
        self.assertEqual(trecho['historico_nomes'], [])
        self.assertEqual(trecho['conferencia_correios'], 'pendente')
        self.assertEqual(self.consultar('Rua do Comércio, Jardim América, CEP 75650-306'), [])
        for nome, cep in (('Rua Ganganelli', '75650-130'), ('Rua das Flores', '75650-072'),
                          ('Praça da Fonte Luminosa', '75650-144')):
            with self.subTest(nome=nome):
                resultado, = self.consultar(nome)
                self.assertEqual((resultado['bairro'], resultado['cep_publicado']), ('Centro', cep))
                self.assertTrue(any(registro['nome'] == nome for registro in resultado['nomes_historicos']))

    def test_primeiro_uso_copia_base_inicial_sem_sobrescrever_a_base_local(self):
        with tempfile.TemporaryDirectory() as pasta:
            local = Path(pasta) / 'morrinhos.sqlite3'
            with patch.object(acervo, 'BANCO', local):
                with closing(acervo.abrir_banco(local)) as db:
                    self.assertEqual(db.execute('SELECT count(*) FROM observacao_postal').fetchone()[0], 4988)
                self.assertTrue(local.is_file())
                with closing(acervo.abrir_banco(local, escrita=True)) as db, db:
                    db.execute('CREATE TABLE marcador_local (id INTEGER)')
                with closing(acervo.abrir_banco(local)) as db:
                    db.execute('SELECT id FROM marcador_local')
            with closing(acervo.abrir_banco(acervo.BASE_INICIAL)) as db:
                self.assertEqual(db.execute('SELECT count(*) FROM ato_nome').fetchone()[0], 106)
                self.assertEqual(db.execute('SELECT count(*) FROM mudanca_local').fetchone()[0], 0)
                self.assertEqual(db.execute('SELECT count(*) FROM conferencia_correios').fetchone()[0], 0)
                db.execute('ATTACH DATABASE ? AS reimportado', (str(self.banco),))
                for tabela in ('fonte', 'bairro', 'trecho', 'observacao_postal', 'ato_nome', 'equivalencia_trecho', 'nome_historico'):
                    with self.subTest(tabela=tabela):
                        self.assertFalse(db.execute(f'SELECT * FROM main.{tabela} EXCEPT SELECT * FROM reimportado.{tabela}').fetchall())
                        self.assertFalse(db.execute(f'SELECT * FROM reimportado.{tabela} EXCEPT SELECT * FROM main.{tabela}').fetchall())
            with self.assertRaises(ValueError):
                acervo.abrir_banco(acervo.BASE_INICIAL, escrita=True)

    def test_homonimos_conservam_ids_e_ceps_separados(self):
        resultados = self.consultar('Rua 216')
        da_lista_recente = [r for r in resultados if r['fonte_postal_id'] == 'lista-2025-12-bairro']
        self.assertEqual({(r['bairro'], r['cep_publicado']) for r in da_lista_recente}, {
            ('Setor Aeroporto', '75654-123'), ('Vila Santos Dumont', '75654-216')})
        self.assertEqual(len({r['trecho_id'] for r in da_lista_recente}), 2)

    def test_mesmo_cep_com_nomes_distintos_preserva_pendencia(self):
        resultados = self.consultar('75650044')
        self.assertEqual({r['nome_postal_publicado'] for r in resultados}, {
            'Rua 18A', 'Rua 1A'})
        self.assertTrue(all(r['divergencia_postal'] for r in resultados))
        self.assertTrue(all(r['conferencia_correios'] == 'pendente' for r in resultados))

    def test_cep_sem_hifen_na_origem_fica_pesquisavel(self):
        resultados = self.consultar('75656-534')
        outubro = next(r for r in resultados if r['fonte_postal_id'] == 'lista-2025-10')
        self.assertEqual(outubro['bairro'], 'VERA CRUZ')
        self.assertEqual(outubro['observacoes_postais'][0]['cep_original'], '75656534')

    def test_lei_sem_cep_encontra_logradouro(self):
        resultado, = self.consultar('Rua Esperança', '--bairro', 'São Francisco de Assis')
        self.assertEqual(resultado['nome_municipal_documentado'], 'Rua Esperança')
        self.assertIsNone(resultado['cep_publicado'])
        self.assertEqual(resultado['situacao_postal'], 'sem_cep_nas_fontes')

    def test_cep_geral_historico_tem_escopo_municipal(self):
        resultado, = self.consultar('75650-000')
        self.assertEqual(resultado['situacao_postal'], 'cep_geral_historico')
        self.assertIsNone(resultado['bairro'])

    def test_lista_anterior_preserva_povoado_sem_bairro_informado(self):
        resultados = self.consultar('75659-100')
        antigo = next(r for r in resultados if r['fonte_postal_id'] == 'lista-2025-01')
        self.assertEqual(antigo['nome_postal_publicado'], 'Povoado de Rancho Alegre')
        self.assertIsNone(antigo['bairro'])

    def test_conferencia_fica_associada_apenas_a_observacao_escolhida(self):
        banco = Path(self.pasta.name) / 'conferencia.sqlite3'
        with closing(sqlite3.connect(self.banco)) as origem, closing(sqlite3.connect(banco)) as destino:
            origem.backup(destino)
        resultados = self.consultar('75650-044', banco=banco)
        escolhido = next(r for r in resultados if r['fonte_postal_id'] == 'lista-2025-12-bairro')
        result = self.cli(
            'registrar-conferencia', str(escolhido['observacao_postal_id']),
            '--data', '2026-11-24', '--responsavel', 'Operador de teste',
            '--resultado', 'confirmado', '--endereco', 'Rua 18A, Setor Oeste',
            '--evidencia', 'Consulta simulada no banco temporário de teste', banco=banco,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        resultados = self.consultar('75650-044', banco=banco)
        self.assertEqual({r['fonte_postal_id']: r['conferencia_correios'] for r in resultados}, {
            'lista-2025-12-bairro': 'confirmado', 'lista-2025-01': 'pendente',
        })

    def test_mudanca_com_lei_une_listas_sem_apagar_o_endereco_anterior(self):
        resultado, = self.consultar('Avenida Central', '--bairro', 'Conjunto Habitacional Monte Verde')
        self.assertEqual(resultado['nome_postal_publicado'], 'Avenida Padre Kleibe França Ribeiro')
        self.assertEqual(resultado['cep_publicado'], '75652-396')
        self.assertIn('Avenida Central', {o['nome_original'] for o in resultado['observacoes_postais']})
        self.assertFalse(resultado['divergencia_postal'])

    def test_exportacao_excel_mantem_texto_literal_e_protege_celulas(self):
        banco = Path(self.pasta.name) / 'exportacao.sqlite3'
        with closing(sqlite3.connect(self.banco)) as origem, closing(sqlite3.connect(banco)) as destino:
            origem.backup(destino)
            destino.execute("UPDATE ato_nome SET trecho_no_ato = ? WHERE id = 'lei-2295-2007'", (' =1+1',))
            destino.commit()
        arquivo = banco.with_suffix('.csv')
        resultado = self.cli('exportar', str(arquivo), banco=banco)
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        with arquivo.open(encoding='utf-8-sig', newline='') as saida:
            avenida = next(linha for linha in csv.DictReader(saida, delimiter=';')
                           if linha['cep_publicado'] == '75652-396')
        self.assertEqual(avenida['trecho_documentado'], "' =1+1")
        resultado, = self.consultar('75652-396', banco=banco)
        self.assertEqual(resultado['trecho_documentado'], ' =1+1')
        bytes_validos = arquivo.read_bytes()
        repeticao = self.cli('exportar', str(arquivo), banco=banco)
        self.assertNotEqual(repeticao.returncode, 0)
        self.assertEqual(arquivo.read_bytes(), bytes_validos)

    def test_backup_restaurado_conserva_ids_e_historico(self):
        copia = Path(self.pasta.name) / 'copia.sqlite3'
        resultado = self.cli('backup', str(copia))
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        self.assertEqual(self.consultar('Rua 03', '--bairro', 'Jardim América', banco=copia),
                         self.consultar('Rua 03', '--bairro', 'Jardim América'))
        with closing(sqlite3.connect(copia)) as db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchall(), [('ok',)])

    def test_busca_ampla_por_bairro_mantem_as_correspondencias(self):
        resultados = self.consultar('Rua', '--bairro', 'Setor Aeroporto')
        ruas = {r['nome_postal_publicado'] for r in resultados if r['bairro'] == 'Setor Aeroporto'}
        self.assertIn('Rua 216', ruas)
        self.assertIn('Rua João Ferreira de Macedo', ruas)
        self.assertNotIn('Rua Juvercina Cipriana da Silva', ruas)

    def test_revisao_de_ato_remove_vinculo_anterior_e_mantem_as_fontes(self):
        caminho = Path(self.pasta.name) / 'revisao.sqlite3'
        self.assertEqual(self.cli('backup', str(caminho)).returncode, 0)
        dados = json.loads((ROOT / 'dados/fontes.json').read_text(encoding='utf-8'))
        ato = next(ato for ato in dados['atos'] if ato['id'] == 'lei-2295-2007')
        del ato['registros_postais_anteriores']
        with closing(acervo.abrir_banco(caminho, escrita=True)) as db, db:
            acervo.importar_ato(db, ato)
            self.assertEqual(db.execute("SELECT count(*) FROM equivalencia_trecho WHERE ato_id = 'lei-2295-2007'").fetchone()[0], 0)
            origens = db.execute("SELECT count(*) FROM observacao_postal WHERE cep = '75652-396'").fetchone()[0]
            self.assertEqual(origens, 5)

    def test_importacao_recusa_mudar_origem_de_fonte_existente(self):
        caminho = Path(self.pasta.name) / 'fontes.sqlite3'
        self.assertEqual(self.cli('backup', str(caminho)).returncode, 0)
        dados = json.loads((ROOT / 'dados/fontes.json').read_text(encoding='utf-8'))
        fonte = dados['listas'][0] | {'referencia': '2030-01-01'}
        with closing(acervo.abrir_banco(caminho, escrita=True)) as db, db:
            with self.assertRaisesRegex(ValueError, 'Mantenha a fonte original'):
                acervo.importar_lista(db, fonte)

    def test_fonte_fora_da_pasta_do_acervo_e_recusada(self):
        caminho = Path(self.pasta.name) / 'fora.sqlite3'
        pdf = Path(self.pasta.name) / 'arquivo.pdf'
        pdf.write_bytes((ROOT / 'fontes/leis/lei-2295-2007.pdf').read_bytes())
        dados = json.loads((ROOT / 'dados/fontes.json').read_text(encoding='utf-8'))
        ato = next(ato for ato in dados['atos'] if ato['id'] == 'lei-2295-2007') | {'arquivo': os.fspath(pdf)}
        with closing(acervo.abrir_banco(caminho, escrita=True)) as db, db:
            with self.assertRaisesRegex(ValueError, 'pasta do acervo'):
                acervo.importar_ato(db, ato)

    def test_boletim_posterior_preserva_a_situacao_da_lista_integral(self):
        caminho = Path(self.pasta.name) / 'boletim.sqlite3'
        self.assertEqual(self.cli('backup', str(caminho)).returncode, 0)
        with closing(sqlite3.connect(caminho)) as db, db:
            db.execute('''INSERT INTO fonte (id, tipo, referencia, url, abrangencia)
                VALUES ('boletim-teste', 'lista_postal', '2026-01-01', 'https://example.org', 'complementar')''')
            db.execute('''INSERT INTO observacao_postal (trecho_id, fonte_id, pagina, linha, nome_original,
                nome_chave, bairro_original, cep_original, cep)
                SELECT trecho_id, 'boletim-teste', 1, 1, nome_original, nome_chave, bairro_original,
                       cep_original, cep FROM observacao_postal
                WHERE fonte_id = 'lista-2025-12-bairro' AND cep = '75650-281' ''')
        resultado, = self.consultar('Rua 03', '--bairro', 'Jardim América', banco=caminho)
        self.assertEqual(resultado['situacao_postal'], 'publicado_lista_complementar')
        vizinhos = self.consultar('Rua 216', '--bairro', 'Setor Aeroporto', banco=caminho)
        self.assertTrue(any(r['situacao_postal'] == 'publicado_ultima_lista' for r in vizinhos))

    def test_denominacao_repetida_em_lei_posterior_conserva_ambos_os_atos(self):
        resultado, = self.consultar('Rua Edma Ramos', '--bairro', 'Povoado Espraiado')
        self.assertEqual([ato['numero'] for ato in resultado['historico_nomes']], ['2.475', '3.045'])

    def test_renomeacao_parcial_da_perimetral_preserva_os_limites(self):
        resultados = self.consultar('Avenida Perimetral')
        trecho, = (r for r in resultados if r['fonte_municipal_id'] == 'lei-3066-2014')
        self.assertEqual(trecho['nome_municipal_documentado'], 'Avenida Presidente Getúlio Vargas')
        self.assertEqual(trecho['trecho_documentado'], 'Entre a Avenida do Trabalhador e a Estrada do Café')
        self.assertIsNone(trecho['cep_publicado'])

    def test_busca_entende_abreviacao_e_bairro_digitado_com_o_nome(self):
        casos = (
            ('Av. Central, Setor Monte Verde', '75652-396'),
            ('R. 03, Jardim America', '75650-281'),
        )
        for entrada, cep in casos:
            with self.subTest(entrada=entrada):
                resultado, = self.consultar(entrada)
                self.assertEqual(resultado['cep_publicado'], cep)

    def test_busca_de_cep_rotulado_preserva_os_resultados_ambiguos(self):
        esperados = self.consultar('75650-044', '--bairro', 'Setor Oeste')
        self.assertEqual(len(esperados), 2)
        self.assertEqual(self.consultar('CEP 75650044, Setor Oeste'), esperados)

    def test_bairro_abreviado_mantem_mesma_busca_quando_nome_completo_e_conhecido(self):
        resultado, = self.consultar('Rua 216', '--bairro', 'Aeroporto')
        self.assertEqual(resultado['bairro'], 'Setor Aeroporto')
        self.assertEqual(resultado['cep_publicado'], '75654-123')

    def test_endereco_copiado_aceita_numero_quadra_localidade_e_cep_formatado(self):
        resultado, = self.consultar('R. 03, nº 44, Qd. 8, Jardim América, Morrinhos - GO, CEP 75.650-281')
        self.assertEqual(resultado['cep_publicado'], '75650-281')
        self.assertEqual(resultado['nome_municipal_documentado'], 'Rua Juvercina Cipriana da Silva')

    def test_bairro_no_fim_funciona_sem_virgula(self):
        resultado, = self.consultar('Rua 216 Vila Santos Dumont')
        self.assertEqual(resultado['cep_publicado'], '75654-216')

    def test_nome_com_palavras_fora_de_ordem_continua_localizavel(self):
        resultados = self.consultar('Silva Juvercina', '--bairro', 'Jardim América')
        self.assertEqual(resultados[0]['cep_publicado'], '75650-281')

    def test_grafia_aproximada_retorna_sugestao_sem_confirmar_identidade(self):
        resposta = self.cli('consultar', 'Rua Juvercna', '--bairro', 'Jardim América')
        self.assertEqual(resposta.returncode, 0, resposta.stderr)
        dados = json.loads(resposta.stdout)
        self.assertEqual(dados['criterio'], 'aproximada')
        self.assertEqual(dados['resultados'][0]['cep_publicado'], '75650-281')

    def test_cep_especifico_conflitante_e_numero_de_rua_nao_sao_aproximados(self):
        self.assertEqual(self.consultar('Rua 03, Jardim América, CEP 75654-069'), [])
        self.assertEqual(self.consultar('Rua 21699', '--bairro', 'Setor Aeroporto'), [])
        self.assertEqual(self.consultar('CEP 75654-069, Morrinhos - CE'), [])

    def test_cep_geral_com_nome_nao_esconde_o_registro_da_via(self):
        resposta = self.cli('consultar', 'Rua 03, Jardim América, CEP 75650-000')
        self.assertEqual(resposta.returncode, 0, resposta.stderr)
        dados = json.loads(resposta.stdout)
        self.assertEqual(dados['resultados'][0]['cep_publicado'], '75650-281')
        self.assertTrue(dados['cep_geral_informado'])

    def test_rua_210_preserva_tres_atos_e_rastreia_observacao_postal(self):
        resultado, = self.consultar('Rua 210', '--bairro', 'Setor Aeroporto')
        self.assertEqual(resultado['cep_publicado'], '75654-064')
        self.assertEqual([r['numero'] for r in resultado['historico_nomes']], ['1.448', '2.311', '2.822'])
        self.assertEqual(resultado['conferencia_correios'], 'pendente')

    def test_rua_fc03_preserva_os_tres_trechos_documentados(self):
        resultados = self.consultar('Rua FC03')
        ceps = {r['cep_publicado'] for r in resultados if r['fonte_municipal_id'] == 'lei-2793-2011'}
        self.assertEqual(ceps, {'75652-366', '75652-482', '75652-446'})

    def test_numero_no_nome_da_rua_e_distinto_de_numero_predial(self):
        dados = self.consultar('Rua nº 19, Vila Bela')
        self.assertEqual([r['cep_publicado'] for r in dados], ['75654-000'])
        self.assertEqual(self.consultar('Rua 19, Vila Bela'), dados)

    def test_busca_por_cardinais_preserva_trechos_e_bairro(self):
        for escrito, numerico in [('Rua três', 'Rua 03'), ('R. vinte e dois', 'Rua 22'),
                                  ('Rua duzentos e dezesseis', 'Rua 216'),
                                  ('Rua nº três, Jardim América', 'Rua 3, Jardim América')]:
            with self.subTest(escrito=escrito):
                esperado = self.consultar(numerico)
                self.assertTrue(esperado)
                self.assertEqual(self.consultar(escrito), esperado)
        self.assertEqual(acervo.via_numerada('avenida duas'), 'avenida 2')
        self.assertIsNone(acervo.via_numerada('rua tres marias'))

    def test_auditoria_separa_cep_ausente_de_grafia_alterada_entre_edicoes(self):
        with closing(acervo.abrir_banco(self.banco)) as db:
            resumo, _ = auditar_acervo.cobertura(db)
        comparacao = resumo['comparacao_listas_integrais']
        self.assertEqual(resumo['registros_da_lista_integral'], 1021)
        self.assertEqual(len(comparacao['ceps_so_na_anterior']), 14)
        self.assertIn('75659-100', comparacao['ceps_so_na_anterior'])
        self.assertNotIn('75650-294', comparacao['ceps_so_na_anterior'])

    def test_pistas_postais_mostram_fontes_e_vinculos_documentados(self):
        with closing(acervo.abrir_banco(self.banco)) as db:
            resumo, _ = auditar_acervo.cobertura(db, listar_pistas=True)
        pistas = {pista['cep']: pista for pista in resumo['comparacao_listas_integrais']['pistas']}
        dalmes = pistas['75650-294']
        self.assertEqual(dalmes['anterior'][0]['nome'], 'Rua 15')
        self.assertEqual(dalmes['atual'][0]['nome'], 'Rua Dalmes Antônio de Oliveira')
        self.assertTrue(dalmes['vinculo_documentado'])
        self.assertTrue(pistas['75654-596']['vinculo_documentado'])
        self.assertFalse(pistas['75650-042']['vinculo_documentado'])
        boletim, = resumo['comparacao_boletins']
        self.assertNotIn('ceps_so_na_atual', boletim)
        rua214 = next(pista for pista in boletim['pistas'] if pista['cep'] == '75654-069')
        self.assertEqual(rua214['anterior'][0]['nome'], 'RUA 214')
        self.assertTrue(rua214['vinculo_documentado'])

    def test_retificacao_da_rua_04_preserva_grafia_postal_e_homonimo(self):
        legal, = self.consultar('Rua 04', '--bairro', 'Jardim Santa Terezinha I')
        self.assertEqual(legal['nome_municipal_documentado'], 'Rua Eurípedes Mariano da Silva')
        self.assertEqual(legal['cep_publicado'], '75654-596')
        self.assertEqual(legal['nome_postal_publicado'], 'Rua Eurípedes Mariano Borges')
        self.assertEqual([ato['numero'] for ato in legal['historico_nomes']], ['1.575', '1.594'])
        homonimo, = (r for r in self.consultar('75654-616') if r['nome_postal_publicado'] == 'Rua 4')
        self.assertIsNone(homonimo['nome_municipal_documentado'])
        self.assertNotEqual(legal['trecho_id'], homonimo['trecho_id'])

    def test_cnefe_2010_registra_grafias_alternativas_sem_exportar_numero_predial(self):
        caminho = Path(self.pasta.name) / 'cnefe-2010.zip'
        linha = bytearray(b' ' * 558)
        linha[:7] = b'5213806'
        linha[16:19] = b'RUA'
        nome = b'DOMINGOS RICARDO DE SOUZA OU RUA 4'
        linha[66:66 + len(nome)] = nome
        linha[126:131] = b'12345'
        linha[351:357] = b'CENTRO'
        linha[550:558] = b'75650000'
        with ZipFile(caminho, 'w') as arquivo:
            arquivo.writestr('52138060500.TXT', bytes(linha) + b'\r\n')
        resumo = auditar_acervo.cruzar_cnefe(caminho, [], ano=2010, listar_pistas=True)
        self.assertEqual(resumo['linhas_lidas'], 1)
        self.assertEqual(resumo['variantes_explicitas'][0]['nomes'],
                         ['rua domingos ricardo de souza', 'rua 4'])
        self.assertNotIn('12345', json.dumps(resumo))

    def test_varredura_inclui_todos_os_trechos_com_nome_e_preserva_homonimos(self):
        with closing(acervo.abrir_banco(self.banco)) as db:
            alvos = varrer_historico.alvos_do_acervo(db)
            total = db.execute("SELECT count(*) FROM consulta_v1 WHERE situacao_postal <> 'cep_geral_historico'").fetchone()[0]
        self.assertEqual(len(alvos), total)
        indice = varrer_historico.formar_indice(alvos)
        self.assertTrue(all(alvo['termos'] for alvo in alvos.values()))
        achados = varrer_historico.buscar_pagina(indice, 'Na R. 0216 de Morrinhos')
        self.assertEqual({alvos[trecho]['bairro'] for trecho, _ in achados}, {'Setor Aeroporto', 'Vila Santos Dumont'})

    def test_varredura_sinaliza_pdf_ausente_com_resultado_indeterminado(self):
        with closing(acervo.abrir_banco(self.banco)) as db:
            catalogo = {'fontes': [{'id': 'ausente', 'arquivo': 'ausente.pdf'}], 'ocorrencias_conferidas': []}
            resumo = varrer_historico.varrer(db, catalogo, Path(self.pasta.name))
        self.assertEqual(resumo['fontes'][0]['estado'], 'pdf_ausente')
        self.assertTrue(all(not reg['ocorrencias'] for reg in resumo['registros']))


if __name__ == '__main__':
    unittest.main()
