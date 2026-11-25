# Pesquisa de nomes e grafias em Morrinhos (GO)

Use o município IBGE **5213806** como recorte. Pesquise por via, bairro e trecho. Registre o que cada fonte diz, a data da fonte, a página ou item e a informação que ainda falta para fechar o vínculo.

## Reproduzir o cruzamento

Baixe os arquivos municipais em uma pasta local fora do clone. O ZIP de 2010 usa o leiaute de largura fixa publicado pelo IBGE. O de 2022 contém o CSV municipal. [CNEFE 2010](https://ftp.ibge.gov.br/Cadastro_Nacional_de_Enderecos_para_Fins_Estatisticos/Censo_Demografico_2010/GO/52138060500.zip) · [Leiaute 2010](https://ftp.ibge.gov.br/Cadastro_Nacional_de_Enderecos_para_Fins_Estatisticos/Censo_Demografico_2010/Layout.zip) · [CNEFE 2022](https://ftp.ibge.gov.br/Cadastro_Nacional_de_Enderecos_para_Fins_Estatisticos/Censo_Demografico_2022/Arquivos_CNEFE/CSV/Municipio/52_GO/5213806_MORRINHOS.zip)

```powershell
python -X utf8 acervo.py importar
python -X utf8 auditar_acervo.py --pistas --cnefe-2010-zip CAMINHO_2010.zip --cnefe-zip CAMINHO_2022.zip
```

- Em `comparacao_listas_integrais.pistas`, veja os CEPs compartilhados com diferença de via ou bairro após normalização. Cada linha indica fonte, página e posição. `vinculo_documentado` indica que as duas edições já apontam para o mesmo conjunto de trechos registrados. Em `comparacao_boletins`, use os mesmos campos para investigar as listas parciais.
- Em `cnefe_2010` e `cnefe_2022`, use `pistas` para revisar pares de via e localidade sem coincidência exata na última lista postal. `variantes_explicitas` mostra os rótulos em que o próprio censo usa `OU`, com a grafia original. Uma variante pode ser nome numerado, apelido, grafia alternativa ou indicação contextual. A data da coleta ajuda a datar seu uso. A data de vigência de um nome exige documento próprio.
- Comece pelas variantes explícitas e pelas diferenças em que as duas fontes trazem a mesma interseção, quadra ou limite público. Para cada via, busque a designação numerada com e sem zeros, abreviações, iniciais, acentos, nomes expandidos, bairro anterior e atual, vias vizinhas e o CEP. Em PDFs digitalizados, procure também por número de lei e ano, use OCR local e confira a imagem da página. Registre também a fonte e o intervalo pesquisado quando a consulta ficar inconclusiva.

O cruzamento do IBGE usa tipo, título, nome de via e localidade. A saída agrupa vias e omite número predial, coordenadas e complemento. Mantenha os ZIPs fora do Git. Em fonte de obras ou regularização, selecione somente a parte necessária para identificar o trecho público.

## Fontes complementares examinadas

| Fonte | O que buscar | Exemplo de Morrinhos (GO) |
| --- | --- | --- |
| [Portal Nacional de Contratações Públicas](https://pncp.gov.br/app/editais/01789551000149/2026/458) | Busque pelo CNPJ municipal `01.789.551/0001-49` e por pavimentação, drenagem ou iluminação. Consulte a lista de vias, o memorial e as plantas para localizar os limites do trecho. | A lista de pavimentação de 2026 usa `RUA FC 3` no item 02, enquanto a Lei nº 2.793/2011 já registra a denominação Rua Beraldino Vicente de Souza. A lista da obra documenta o uso do código da via e a extensão do serviço. [Anexo, p. 1](https://pncp.gov.br/pncp-api/v1/orgaos/01789551000149/compras/2026/458/arquivos/9) · [Lei nº 2.793/2011](fontes/leis/lei-2793-2011.pdf) |
| [Notícias e mapa da Prefeitura](https://morrinhos.go.gov.br/mapa-da-cidade-de-morrinhos/) | Busque inaugurações, reformas, placas, nomes populares e esquinas. Anote os cruzamentos e compare com a planta da época. | A Prefeitura usa Praça Nossa Senhora do Carmo e Praça da Matriz para a mesma praça, no encontro da Avenida Coronel Pedro Nunes com a Rua Dr. Pedro Nunes. A notícia documenta o nome popular. [Notícia municipal](https://morrinhos.go.gov.br/resumo-das-noticias-da-semana-de-15-a-19-06/) |
| [Editais de regularização fundiária](https://morrinhos.go.gov.br/wp-content/uploads/2025/07/Edital.-REURB.-Setor-Oeste.pdf#page=2) e cadastro municipal | Busque o loteamento pelo nome original, pelo nome atual e pelo processo. Quando a planta ou o memorial estiver disponível, compare quadras, vias e a descrição do perímetro. | O edital de 09/07/2025 identifica Rua Geraldo Santana no Setor Oeste. A Lei nº 2.517/2009 registra que a designação anterior era Rua 13. [Lei nº 2.517/2009](fontes/leis/lei-2517-2009.pdf) |
| [Cadastro estadual de escolas](https://goias.gov.br/educacao/lista-de-escolas-rede-estadual-de-educacao/), [CNES](https://cnes.datasus.gov.br/) e diários oficiais | Use equipamentos públicos como pontos de referência para cruzar grafias e bairros. Busque a mesma unidade em edições de anos diferentes. | A rede estadual registra `AV JOSE NASCIMENTO` no Setor Oeste para o colégio Xavier de Almeida. A Lei nº 1.576/1998 comprova a mudança de denominação. A localização do trecho postal precisa de conferência própria. [Lei nº 1.576/1998](fontes/leis/lei-1576-1998.pdf) |
| [Hemeroteca do IHGG](https://hemeroteca.ihgg.org/) e [Arquivo Histórico de Goiás](https://goias.gov.br/cultura/indice-arquivo-historico-de-goias/) | Pesquise também por grafia da época, título do periódico, anúncio, prédio público e cruzamento. Use a edição, a data e a página para comprovar o uso. | O catálogo do IHGG lista o jornal de Morrinhos *O Liberal*. Para períodos sem texto indexado, procure a edição no acervo físico e examine o fac-símile. |

## Resultado do cruzamento de 25/11/2026

| Base oficial do IBGE | Linhas lidas | Pares de via nomeada e localidade | Coincidências exatas com a lista de dezembro de 2025 | Pares para triagem | Rótulos com `OU` por localidade |
| --- | ---: | ---: | ---: | ---: | ---: |
| CNEFE 2010 | 21.206 | 726 | 278 | 448 | 28 |
| CNEFE 2022 | 31.384 | 1.100 | 354 | 746 | 3 |

Entre as listas integrais de janeiro e dezembro de 2025, 165 CEPs compartilhados têm diferença de nome ou bairro. O boletim de outubro tem 25 diferenças em CEPs compartilhados com dezembro. Um CEP pode aparecer em mais de uma comparação. A unidade do CNEFE é o par textual de via e localidade. As contagens incluem diferenças de grafia e recorte geográfico, por isso medem o volume de triagem. [Listas postais da Prefeitura](https://morrinhos.go.gov.br/codigo-de-enderecamento-postal-cep/)

No Setor Aeroporto, o CNEFE 2010 traz `RUA 214 OU JOAO F MACEDO` e `AVENIDA 100 OU PROFESSORA ZILDA DINIZ FONTES`. No Centro, traz `RUA DOMINGOS RICARDO DE SOUZA OU RUA 4`. Use esses rótulos para procurar publicações municipais pelos dois nomes e confirmar os limites em planta. As leis examinadas e os vínculos ainda em pesquisa ficam no [índice legislativo](LEGISLACAO.md).

## Varredura histórica por nome de logradouro

O [catálogo histórico](dados/pesquisa-historica.json) indica os PDFs, as páginas, o hash SHA-256 e as ocorrências conferidas. Baixe os seis PDFs na mesma pasta, com os nomes do catálogo. O seguinte comando lê os nomes postais de todas as edições, os nomes dos atos municipais e os nomes históricos catalogados. Com os ZIPs, inclui também os pares de via nomeada e localidade dos dois censos, com as alternativas registradas sob `OU`.

```powershell
python -X utf8 varrer_historico.py --pasta-fontes CAMINHO_DOS_PDFS --cnefe-2010-zip CAMINHO_2010.zip --cnefe-zip CAMINHO_2022.zip |
    Set-Content -Encoding utf8 morrinhos-varredura-historica.json
```

Cada registro conserva o ID do trecho ou identifica a época e localidade da observação censitária. O relatório lista os termos efetivamente pesquisados e a página de cada ocorrência. A busca normaliza abreviações, acentos e zeros em vias numeradas. Nomes iguais em bairros diferentes podem apontar para a mesma página, por isso cada ocorrência exige revisão de município, bairro e trecho na própria fonte. PDFs ausentes, extrações incompletas e páginas sem texto aparecem com seus estados no relatório. Mantenha a saída e os PDFs de pesquisa fora do Git.

### Fontes antigas já examinadas

| Época do registro | Fonte | O que foi localizado |
| --- | --- | --- |
| 1892 | [Viagem às Terras Goyanas, páginas 62–63 do PDF](https://bibliotecafuturo.com.br/wp-content/uploads/tainacan-items/52/9513/VIAGEM-AS-TERRAS-GOIANAS.pdf#page=62) | Relato de Oscar Leal sobre a cidade e as ruas. As páginas examinadas descrevem a vila, o espaço urbano e seus melhoramentos sem identificar logradouros por nome. |
| 1896 | [Dissertação de Maria Lúcia Fonseca, quadro 1 e indicação da fonte, páginas 50–51](https://files.cercomp.ufg.br/weby/up/113/o/FONSECA__Maria_L_cia._1997.pdf#page=50) | Onze logradouros transcritos do **Imposto Sobre o Valor Locativo dos Prédios Urbanos de 1896**, Arquivo Histórico de Goiás, **caixa 04 de Morrinhos**. A transcrição e sua indicação arquivística foram conferidas. A consulta ao lançamento original está pendente. |
| 1924 e 1926 | [Dissertação de Eron Meneses de Amorim, página 172](https://files.cercomp.ufg.br/weby/up/113/o/AMORIM__Eron_Meneses_de._1998.pdf#page=172) · [Tese de Júlio Cesar Meira, página 103](https://repositorio.ufu.br/bitstream/123456789/21352/1/IdeiasProgressoModernizacao.pdf#page=103) | Legendas identificam Rua Barão do Rio Branco e a bifurcação das ruas Goiás e Barão do Rio Branco na Avenida Coronel Pedro Nunes. Servem para localizar o núcleo antigo. |
| 1968 | [Jornal do Povo, edição de 05/08/1968, página 1](https://hemeroteca.ihgg.org/publicacoes/JORNAL_DO_POVO/1968/08/JORNAL_DO_POVO_1968_08_05.pdf#page=1) | Foto e reportagem sobre a Vila Bela de Morrinhos. A página documenta o nome do conjunto nessa data. |
| Década de 1970 | [Mapa da área urbana na tese de Meira, página 178 do PDF](https://repositorio.ufu.br/bitstream/123456789/21352/1/IdeiasProgressoModernizacao.pdf#page=178) | A planta distingue a área urbanizada até 1964 da expansão da década de 1970. Serve para orientar a pesquisa por setores. As legendas cartográficas exigem leitura visual. |

### Nomes registrados em 1896

| Grafia no levantamento | Correspondência encontrada em pesquisa histórica |
| --- | --- |
| Rua do Açude | A confirmar |
| Rua do Dr. Antero | A confirmar |
| Rua Boa Vista | A confirmar |
| Rua Ganganelli | Rua Minas Gerais, no local da antiga escola descrita por Fonseca. [Página 80](https://files.cercomp.ufg.br/weby/up/113/o/FONSECA__Maria_L_cia._1997.pdf#page=80) |
| Rua das Flores | Avenida Coronel Pedro Nunes, no local do sobrado citado por Fonseca. [Página 94](https://files.cercomp.ufg.br/weby/up/113/o/FONSECA__Maria_L_cia._1997.pdf#page=94) |
| Rua da Matriz | A confirmar |
| Rua de São Paulo | A confirmar |
| Rua do Brejo | A confirmar |
| Largo da Liberdade | A confirmar. O relato citado por Meira liga **Praça da Liberdade**, com outra grafia, a Largo do Rosário e Praça Rui Barbosa. [Página 100 do PDF](https://repositorio.ufu.br/bitstream/123456789/21352/1/IdeiasProgressoModernizacao.pdf#page=100) |
| Rua do Comércio | Rua Barão do Rio Branco, no trecho antigo do Centro. [Fonseca, p. 42](https://files.cercomp.ufg.br/weby/up/113/o/FONSECA__Maria_L_cia._1997.pdf#page=42) · [Santos, p. 30](https://repositorio.bc.ufg.br/riserver/api/core/bitstreams/07d83e25-5f77-473c-9e26-1d572b6354e5/content#page=30) |
| Rua Direita | A confirmar |

As correspondências históricas acima indicam o uso dos nomes e sua localização no núcleo antigo. O alcance, a data da mudança e o ato municipal exigem fontes próprias. Para aprofundar a pesquisa, procure a caixa **04 de Morrinhos** e as séries da Câmara, Intendência e Prefeitura, com livros de atas, posturas, emplacamento, imposto predial e aprovação de loteamentos. Em periódicos do século XIX, inclua `Goyaz` e `Villa Bella de Morrinhos` nas buscas. Confira o município no texto original antes de extrair um nome. [Arquivo Histórico de Goiás](https://goias.gov.br/cultura/indice-arquivo-historico-de-goias/) · [Hemeroteca Digital Brasileira](https://bndigital.bn.gov.br/hemeroteca-digital/) · [Histórico do município no IBGE](https://www.ibge.gov.br/biblioteca/visualizacao/dtb/goias/morrinhos.pdf)

O [índice de anexos da Prefeitura](https://morrinhos.go.gov.br/wp-json/wp/v2/media?search=logradouro&per_page=100&_fields=source_url,title) complementa os índices de legislação. Repita com `denominacao`, `altera nome`, `nome de rua`, `via publica`, número do ato e nome do homenageado. Confira o total informado pelo cabeçalho `X-WP-Total` e deduplique as URLs. A busca examina metadados de anexos. Leia o inteiro teor antes de registrar um ato. A consulta desta rodada localizou a [Lei nº 2.980/2013](fontes/leis/lei-2980-2013.pdf), que dá nome à praça Antônio Rosa Ribeiro – Falcão em uma rotatória. O mesmo homenageado aparece em ruas de outros bairros nas listas postais.

### Resultado da execução de 25/11/2026

Foram pesquisadas **216 páginas com texto** em seis fontes. Uma página no intervalo selecionado ficou sem texto extraível. Os pares por censo e os trechos da base podem se referir à mesma via, com fonte e época próprias.

| Registros pesquisados | Total com termos | Com possível ocorrência textual |
| --- | ---: | ---: |
| Trechos com nome no acervo | 1.244 | 68 |
| Pares de via e localidade no CNEFE 2010 | 726 | 57 |
| Pares de via e localidade no CNEFE 2022 | 1.100 | 62 |
| Ocorrências históricas conferidas e catalogadas | 12 | 12 |

O resultado cobre os nomes dessas listas e os intervalos de páginas documentados. A revisão individual das coincidências, das fontes físicas e dos períodos sem documentos digitalizados continua em aberto. Nenhum CEP foi conferido diretamente nos Correios nesta rodada.
