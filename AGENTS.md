# Instruções para manter e revisar o acervo

O repositório documenta vias de **Morrinhos, Goiás, código IBGE 5213806**, para consulta no cartório. O [README](README.md) explica como executar a aplicação. O [plano](PLANO.md) define o que significa cobrir um bairro e o [índice legislativo](LEGISLACAO.md) documenta os atos já examinados.

## Reproduzir a base e validar uma mudança

Use Python 3.10 ou superior, SQLite da biblioteca padrão e `pdftotext` do Poppler no PATH. Execute na raiz do clone.

```powershell
python -X utf8 acervo.py importar
python -X utf8 -B -m unittest discover -s tests -v
python -X utf8 auditar_acervo.py
python -X utf8 interface.py
```

Abra [a interface local](http://127.0.0.1:8765). A consulta é somente leitura. `busca.py` interpreta entradas e variantes. `acervo.py` resolve candidatos, evidências e vínculos no SQLite. `interface.py` expõe à tela apenas os campos de consulta e `web/` contém os arquivos do navegador.

Em uma base que guarde conferências reais, faça uma cópia com `python -X utf8 acervo.py backup minha-copia.sqlite3` e valide a mudança nela com `--banco minha-copia.sqlite3` antes de aplicá-la ao banco de trabalho. O banco local, exportações, backups e credenciais ficam fora do Git. Preserve alterações locais feitas pela equipe.

## Ampliar a pesquisa rua por rua

1. Rode `auditar_acervo.py` e use a contagem de pendências por bairro para escolher o próximo lote. Pesquise cada via pelo nome atual, designação numerada, tipo abreviado, títulos com e sem abreviação, bairro atual e histórico, loteamento, interseções e CEPs antigos. Use os limites do trecho quando houver homônimos.
2. Compare as edições das listas postais, os boletins complementares, o cadastro de logradouros e o mapa municipal. Use o CNEFE do IBGE como triagem independente. Um nome que só aparece numa fonte pode refletir mudança de grafia, de bairro ou de cobertura. [Listas da Prefeitura](https://morrinhos.go.gov.br/codigo-de-enderecamento-postal-cep/) · [Mapa municipal](https://morrinhos.go.gov.br/mapa-da-cidade-de-morrinhos/) · [CNEFE 2022 de Morrinhos (GO)](https://ftp.ibge.gov.br/Cadastro_Nacional_de_Enderecos_para_Fins_Estatisticos/Censo_Demografico_2022/Arquivos_CNEFE/CSV/Municipio/52_GO/5213806_MORRINHOS.zip)
3. Busque nos índices da Prefeitura e Câmara e no diário oficial pelos dois nomes e pelos termos `denominação`, `dá nome`, `altera nome`, `logradouro`, `loteamento` e `numeração`. Abra o ato completo e confira a jurisdição, o número no cabeçalho, o artigo, a página, os limites, eventuais anexos, retificações e leis posteriores. Quando cabível, verifique as comunicações municipais que chegaram ao Registro Geral de Imóveis. [Câmara Municipal](https://leis.morrinhos.go.leg.br/leis) · [Diário Oficial dos Municípios Goianos](https://www.diariomunicipal.com.br/agm/pesquisar) · [Lei nº 3.091/2014, arts. 22 e 27](fontes/leis/lei-3091-2014.pdf#page=7)
4. Arquive o PDF oficial, cite o link e registre o ato em `dados/fontes.json` e em `LEGISLACAO.md`. Preserve a grafia original, a data do ato e a data de vigência quando documentada. Para ato com várias vias ou trechos, use um `registro` distinto por ocorrência. Use `trecho_ato` para encadear atos sobre o mesmo trecho, `vinculo_postal` para apontar a linha postal comprovada e `registros_postais_anteriores` ou `registros_postais_vinculados` para preservar variantes confirmadas de fontes diferentes.
5. Registre separadamente as pistas, o que cada fonte prova e a evidência que falta. Mesmo CEP, nome semelhante, bairro vizinho ou coincidência de ordem entre duas leis são sinais para investigar. Use **histórico a confirmar** quando faltar evidência e mantenha os registros ambíguos disponíveis. Um trecho sem CEP localizado permanece pesquisável pelo ato da Prefeitura.
6. Para marcar um CEP como conferido, guarde a consulta direta ao Busca CEP ou a referência da edição oficial do DNE usada pelo cartório. Compare via, bairro, município e trecho. Anote data, resultado e evidência conforme `acervo.py registrar-conferencia --help`. As listas publicadas pela Prefeitura e as pistas do IBGE documentam observações, com origem própria. [Busca CEP](https://buscacepinter.correios.com.br/app/endereco/index.php) · [DNE dos Correios](https://www.correios.com.br/enviar/precisa-de-ajuda/guia-de-enderecamento/guia-de-enderecamento)

Se o ZIP oficial do CNEFE 2022 estiver disponível, faça o cruzamento agregado com `python -X utf8 auditar_acervo.py --cnefe-zip CAMINHO_DO_ZIP`. Ele lê o arquivo municipal e informa contagens por localidade. As contagens de pares exatos são uma medida de comparação textual, com diferenças de época, tipo de via e grafia. Use o ZIP apenas na pesquisa local e preserve no acervo somente os dados públicos do logradouro necessários ao projeto.

## Validar a busca e a interface

Teste no CLI e no navegador. Preserve o ID do trecho, a procedência e todas as correspondências do mesmo nível de evidência. A busca flexível amplia candidatos. Ela nunca cria vínculos históricos por conta própria.

| Entrada | O que conferir |
|---|---|
| `Rua 216` e `Rua 216 Vila Santos Dumont` | Dois homônimos sem bairro. Com Vila Santos Dumont, retorna o CEP `75654-216`. |
| `R. 03, nº 44, Qd. 8, Jardim América, Morrinhos - GO, CEP 75.650-281` | Encontra a Rua Juvercina Cipriana da Silva. Os complementos são contexto de busca. |
| `Rua Juvercna` com Jardim América | Aparece como sugestão aproximada. A interface aguarda a seleção para mostrar o detalhe. |
| `Rua nº 19, Vila Bela` e `Rua FC03` | O número do nome da via é preservado. Os trechos com bairros e CEPs próprios continuam separados. |
| `Rua 210, Setor Aeroporto` | Mostra os atos de 1996, 2007 e 2011, a grafia postal e a divergência de referência legal. |
| `75654-069` | Mantém visíveis Rua 214 e Rua João Ferreira de Macedo como registros distintos. |
| `75650-000` sozinho e junto do nome de uma via | Sozinho é um CEP geral histórico. Com nome e bairro, funciona como contexto da busca. |
| `Rua 03, Jardim América, CEP 75654-069` ou `CEP 75654-069, Morrinhos - CE` | A busca conserva as restrições informadas e evita apresentar uma via de outro contexto. |

Para outra IA revisar o projeto, peça que execute os testes, verifique os casos da tabela, leia os artigos dos PDFs que sustentam uma mudança e compare as contagens antes e depois. Peça uma lista de achados com arquivo, linha, fonte e passos de verificação, incluindo exemplos positivos e negativos. Para cada ponto pendente, peça a fonte necessária para aprofundar a verificação. Mantenha o banco de teste separado do banco de trabalho e examine os campos expostos pela API antes de integrar ao software do cartório.
