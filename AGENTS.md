# Instruções para manter e revisar o acervo

O repositório documenta vias de **Morrinhos, Goiás, código IBGE 5213806**, para consulta no cartório. O [README](README.md) explica como executar a aplicação. O [plano](PLANO.md) define o que significa cobrir um bairro e o [índice legislativo](LEGISLACAO.md) documenta os atos já examinados.

## Reproduzir a base e validar uma mudança

Use Python 3.10 ou superior e SQLite da biblioteca padrão. A interface cria a cópia local a partir de `dados/base-inicial.sqlite3` no primeiro uso. Para reimportar as fontes ou executar os testes, tenha `pdftotext` do Poppler no PATH. Execute na raiz do clone.

```powershell
python -X utf8 acervo.py importar
python -X utf8 -B -m unittest discover -s tests -v
python -X utf8 auditar_acervo.py
python -X utf8 interface.py
```

Abra [a interface local](http://127.0.0.1:8765). O modo padrão é somente leitura. Para registrar uma mudança pela interface, use `python -X utf8 interface.py --edicao` e consulte o [procedimento no README](README.md#cadastrar-uma-mudança-na-interface). `busca.py` interpreta entradas e variantes. `acervo.py` resolve evidências, vínculos e cadastros no SQLite. `interface.py` atende a interface local e `web/` contém os arquivos do navegador.

Em uma base que guarde conferências reais, faça uma cópia com `python -X utf8 acervo.py backup minha-copia.sqlite3` e valide a mudança nela com `--banco minha-copia.sqlite3` antes de aplicá-la ao banco de trabalho. O banco local, exportações, backups e credenciais ficam fora do Git. Preserve alterações locais feitas pela equipe.

Quando mudar as fontes importadas ou o esquema, rode `python -X utf8 acervo.py gerar-base-inicial dados/base-inicial-nova.sqlite3`. O comando recria o banco do zero com o catálogo público. Após conferir a integridade e as contagens, substitua `dados/base-inicial.sqlite3` pelo novo arquivo e rode os testes. Publique como base inicial somente o arquivo gerado a partir das fontes públicas. As tabelas de mudanças locais e conferências dos Correios devem estar vazias.

## Ampliar a pesquisa rua por rua

1. Rode `auditar_acervo.py` e use a contagem de pendências por bairro para escolher o próximo lote. Pesquise cada via pelo nome atual, designação numerada, tipo abreviado, títulos com e sem abreviação, bairro atual e histórico, loteamento, interseções e CEPs antigos. Use os limites do trecho quando houver homônimos.
2. Compare as edições das listas postais, os boletins complementares, o cadastro de logradouros e o mapa municipal. Use o CNEFE do IBGE como triagem independente. Um nome que só aparece numa fonte pode refletir mudança de grafia, de bairro ou de cobertura. [Listas da Prefeitura](https://morrinhos.go.gov.br/codigo-de-enderecamento-postal-cep/) · [Mapa municipal](https://morrinhos.go.gov.br/mapa-da-cidade-de-morrinhos/) · [CNEFE 2022 de Morrinhos (GO)](https://ftp.ibge.gov.br/Cadastro_Nacional_de_Enderecos_para_Fins_Estatisticos/Censo_Demografico_2022/Arquivos_CNEFE/CSV/Municipio/52_GO/5213806_MORRINHOS.zip)
3. Busque nos índices da Prefeitura e Câmara e no diário oficial pelos dois nomes e pelos termos `denominação`, `dá nome`, `altera nome`, `logradouro`, `loteamento` e `numeração`. Abra o ato completo e confira a jurisdição, o número no cabeçalho, o artigo, a página, os limites, eventuais anexos, retificações e leis posteriores. Quando cabível, verifique as comunicações municipais que chegaram ao Registro Geral de Imóveis. [Câmara Municipal](https://leis.morrinhos.go.leg.br/leis) · [Diário Oficial dos Municípios Goianos](https://www.diariomunicipal.com.br/agm/pesquisar) · [Lei nº 3.091/2014, arts. 22 e 27](fontes/leis/lei-3091-2014.pdf#page=7)
4. Arquive o PDF oficial, cite o link e registre o ato em `dados/fontes.json` e em `LEGISLACAO.md`. Preserve a grafia original, a data do ato e a data de vigência quando documentada. Para ato com várias vias ou trechos, use um `registro` distinto por ocorrência. Use `trecho_ato` para encadear atos sobre o mesmo trecho, `vinculo_postal` para apontar a linha postal comprovada e `registros_postais_anteriores` ou `registros_postais_vinculados` para preservar variantes confirmadas de fontes diferentes.
   Use como fonte principal o PDF assinado publicado pela Prefeitura. Confira o número, o ano, o artigo e a assinatura no documento e registre a URL direta e `pdf_prefeitura_assinado: true` em todas as ocorrências do ato. Mantenha a ficha oficial em `ficha_prefeitura`. Se a versão municipal assinada ainda estiver pendente, documente a busca e identifique o exemplar disponível como referência.
   O campo `tipo_alteracao` identifica a natureza do ato. Use `nota_ato` para ressalvas da ocorrência. Para uma lei cuja única fonte disponível seja a cópia local, use a URL relativa `/fontes/leis/lei-NNN-AAAA.pdf` correspondente ao PDF público catalogado.
5. Registre separadamente as pistas, o que cada fonte prova e a evidência que falta. Mesmo CEP, nome semelhante, bairro vizinho ou coincidência de ordem entre duas leis são sinais para investigar. Use **histórico a confirmar** quando faltar evidência e mantenha os registros ambíguos disponíveis. Um trecho sem CEP localizado permanece pesquisável pelo ato da Prefeitura.
6. Para marcar um CEP como conferido, guarde a consulta direta ao Busca CEP ou a referência da edição oficial do DNE usada pelo cartório. Compare via, bairro, município e trecho. Anote data, resultado e evidência conforme `acervo.py registrar-conferencia --help`. As listas publicadas pela Prefeitura e as pistas do IBGE documentam observações, com origem própria. [Busca CEP](https://buscacepinter.correios.com.br/app/endereco/index.php) · [DNE dos Correios](https://www.correios.com.br/enviar/precisa-de-ajuda/guia-de-enderecamento/guia-de-enderecamento)

Use `--pistas` para abrir a comparação detalhada das listas integrais e dos boletins. Com os ZIPs oficiais, use `--cnefe-2010-zip` e `--cnefe-zip` para comparar os dois censos com a lista postal por localidade. O [roteiro de pesquisa](PESQUISA.md) traz os comandos, os limites do cruzamento e exemplos de fontes complementares. Use os ZIPs somente na pesquisa local e preserve no acervo apenas os dados públicos do logradouro necessários ao projeto.

Para pesquisar todos os nomes cadastrados em um conjunto de PDFs, execute `varrer_historico.py` conforme o [roteiro histórico](PESQUISA.md#varredura-histórica-por-nome-de-logradouro). Confira a página e o contexto de cada ocorrência. O relatório conserva os homônimos e registra quando faltou um PDF ou texto extraível. Ao acrescentar uma fonte, indique URL, hash da edição, data, páginas e jurisdição no [catálogo histórico](dados/pesquisa-historica.json).

Para tornar um nome antigo ou popular pesquisável pela interface, registre em `ocorrencias_conferidas` a página de uso do nome e a `pagina_correspondencia` que identifica o mesmo trecho. Preencha `vinculo_postal` com nome, bairro e CEP exatos da observação e explique o alcance em `nota_vinculo`. Pesquise prédios públicos, praças, esquinas e plantas para localizar o trecho. Deixe o vínculo em aberto enquanto a evidência for insuficiente.

## Validar a busca e a interface

Teste no CLI e no navegador. Preserve o ID do trecho, a procedência e todas as correspondências do mesmo nível de evidência. A busca flexível amplia candidatos. Ela nunca cria vínculos históricos por conta própria.

| Entrada | O que conferir |
|---|---|
| `Rua 216` e `Rua 216 Vila Santos Dumont II` | Dois homônimos sem bairro. Com Vila Santos Dumont II, retorna o CEP `75654-350`. |
| `R. 03, nº 44, Qd. 8, Jardim América, Morrinhos - GO, CEP 75.650-281` | Encontra a Rua Juvercina Cipriana da Silva. Os complementos são contexto de busca. |
| `Rua Juvercna` com Jardim América | Aparece como sugestão aproximada. A interface aguarda a seleção para mostrar o detalhe. |
| `Rua nº 19, Vila Bela` e `Rua FC03` | O número do nome da via é preservado. Os trechos com bairros e CEPs próprios continuam separados. |
| `Rua 210, Setor Aeroporto` | Mostra os atos de 1996, 2007 e 2011, a grafia postal e a divergência de referência legal. |
| `75654-069` | Encontra as observações postais de Rua 214 e Rua João Ferreira de Macedo no trecho documentado pela Lei nº 805/1988. |
| `75650-000` sozinho e junto do nome de uma via | Sozinho é um CEP geral histórico. Com nome e bairro, funciona como contexto da busca. |
| `Rua 03, Jardim América, CEP 75654-069` ou `CEP 75654-069, Morrinhos - CE` | A busca conserva as restrições informadas e evita apresentar uma via de outro contexto. |
| Nome em branco, `Povoado de Marcelânia`, `CEP a definir no cadastro` | Lista a Rua Dona Etelvina Rosa de Jesus. Em uma cópia de teste, cadastrar um CEP específico retira o trecho dessa fila e o preserva em `Sem CEP atual nas fontes`. |

Para outra IA revisar o projeto, peça que execute os testes, verifique os casos da tabela, leia os artigos dos PDFs que sustentam uma mudança e compare as contagens antes e depois. Peça uma lista de achados com arquivo, linha, fonte e passos de verificação, incluindo exemplos positivos e negativos. Para cada ponto pendente, peça a fonte necessária para aprofundar a verificação. Mantenha o banco de teste separado do banco de trabalho e examine os campos expostos pela API antes de integrar ao software do cartório.
