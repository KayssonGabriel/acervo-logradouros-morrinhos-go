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
