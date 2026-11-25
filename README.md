<img src="web/marca.svg" width="56" height="56" align="right" alt="">

# Acervo de logradouros de Morrinhos, Goiás

Pesquise ruas pelo nome antigo, pelo nome atual ou pelo CEP. Veja o bairro, o trecho e os documentos que sustentam cada resultado. A consulta funciona no navegador do seu computador e já vem com uma base preenchida.

[Começar](#começar) · [Exemplos de busca](#exemplos-de-busca) · [Cadastrar uma mudança](#cadastrar-uma-mudança-na-interface) · [Contribuir](#contribuir) · [Dados e fontes](#dados-e-fontes)

## Começar

**Você precisa de Python 3.10 ou superior.** Com Git instalado, rode os comandos abaixo no terminal. Você também pode baixar o projeto pelo botão **Code → Download ZIP**, extrair o arquivo e abrir o terminal na pasta extraída.

```sh
git clone https://github.com/KayssonGabriel/acervo-logradouros-morrinhos-go.git
cd acervo-logradouros-morrinhos-go
python -X utf8 interface.py
```

Abra **[http://127.0.0.1:8765](http://127.0.0.1:8765)**. No primeiro uso, o programa cria `morrinhos.sqlite3` a partir da [base inicial](dados/base-inicial.sqlite3). Você já pode consultar sem instalar o Poppler, importar PDFs ou entrar no GitHub. Mantenha o terminal aberto enquanto estiver usando a interface.

Se o comando `python` estiver indisponível, tente `py -3` no Windows ou `python3` no macOS e Linux. Se a porta 8765 estiver ocupada, inicie com `python -X utf8 interface.py --porta 8766` e abra [http://127.0.0.1:8766](http://127.0.0.1:8766).

## Exemplos de busca

| Digite | O que aparece |
| --- | --- |
| `Rua 03, Jardim América` | Rua Juvercina Cipriana da Silva, CEP `75650-281`, com a lei que documenta o nome. |
| `Rua 216` | Dois resultados, em Setor Aeroporto e Vila Santos Dumont. Selecione o bairro do endereço. |
| `Rua 04, Jardim Santa Terezinha I` | O histórico mostra a sequência Rua 04 → Rua Eurípedes Mariano Borges → Rua Eurípedes Mariano da Silva. A lista postal de dezembro de 2025 usa a denominação Borges para o CEP `75654-596`. |
| `75654-069` | Rua 214 e Rua João Ferreira de Macedo, com as respectivas fontes. A equivalência entre os registros está em pesquisa. |
| `75650-000` | O CEP geral histórico de Morrinhos. Para identificar um trecho específico, informe também a via e o bairro. |

A busca aceita abreviações como `R.` e `Av.`, grafias sem acento e endereços com CEP. Um resultado por grafia semelhante aparece como sugestão. Confirme o bairro, o trecho e a fonte antes de usar a informação.

### Como interpretar um resultado

| Campo | Significado |
| --- | --- |
| **Nome municipal documentado** | Denominação encontrada em ato municipal, com o artigo e a data disponíveis no histórico. |
| **CEP publicado** | CEP observado numa lista postal, com a referência da edição. A data da lista indica quando a informação foi publicada. |
| **Conferência nos Correios** | Resultado de uma consulta direta registrada para a observação postal. A base inicial tem as conferências pendentes. |
| **Mudanças cadastradas** | Histórico lançado por quem usa a cópia local, com a vigência quando conhecida e a referência informada. |

## Cadastrar uma mudança na interface

Feche o servidor de consulta com `Ctrl+C` e inicie o modo de edição:

```sh
python -X utf8 interface.py --edicao
```

1. Busque a via, selecione o trecho correto e clique em **Cadastrar mudança**.
2. Informe o novo nome. Preencha o nome anterior e a vigência se forem conhecidos. Para uma alteração somente de CEP, deixe os nomes em branco.
3. Selecione **Mudou**, **Continuou igual** ou **Ainda a confirmar**. Preencha os campos de CEP de acordo com a fonte.
4. Informe a referência documental e, se houver, um link público. Ao salvar, o registro aparece em **Mudanças cadastradas**. Você pode recuperar o trecho pelos nomes e CEPs específicos registrados.

O modo de edição permite gravar no banco desse computador. A referência digitada fica visível na consulta. Use referências públicas e preserve a cópia local em backup. Os lançamentos locais continuam no seu computador e aparecem junto das fontes importadas na interface.

## Dados e fontes

O recorte é **Morrinhos, Goiás (IBGE 5213806)**. A [base inicial](dados/base-inicial.sqlite3) reúne **4.988 observações postais** de várias edições e **46 registros de atos municipais**. A lista integral de dezembro de 2025 traz **1.021 registros postais**. As contagens maiores incluem observações repetidas entre edições e entre as ordenações por bairro e por nome.

| Informação | Onde consultar |
| --- | --- |
| Listas postais, boletins e mapa | [Listas da Prefeitura](https://morrinhos.go.gov.br/codigo-de-enderecamento-postal-cep/) · [Mapa municipal](https://morrinhos.go.gov.br/mapa-da-cidade-de-morrinhos/) |
| Atos de denominação e renomeação | [Índice legislativo e PDFs](LEGISLACAO.md) · [Leis da Câmara](https://leis.morrinhos.go.leg.br/leis) |
| Nomes antigos, jornais, plantas e censos | [Roteiro de pesquisa histórica](PESQUISA.md) · [Catálogo de fontes históricas](dados/pesquisa-historica.json) |
| Proveniência e edições das fontes importadas | [Catálogo de fontes do banco](dados/fontes.json) |
| Conferência postal direta | [Busca CEP dos Correios](https://buscacepinter.correios.com.br/app/endereco/index.php) |

O levantamento fiscal de 1896, reproduzido em pesquisa da UFG, já identifica 11 logradouros de Morrinhos. O roteiro documenta as correspondências históricas localizadas, as fontes consultadas e os pontos que ainda exigem pesquisa individual. [Levantamento de 1896, p. 50](https://files.cercomp.ufg.br/weby/up/113/o/FONSECA__Maria_L_cia._1997.pdf#page=50) · [Resultados da pesquisa](PESQUISA.md#nomes-registrados-em-1896)

## Exportar, atualizar e fazer backup

```sh
# Gerar uma planilha em formato CSV
python -X utf8 acervo.py exportar morrinhos.csv

# Gerar uma cópia de segurança verificada do banco local
python -X utf8 acervo.py backup morrinhos-copia.sqlite3

# Consultar por nome e bairro em JSON
python -X utf8 acervo.py consultar "Rua 03" --bairro "Jardim América"
```

Use um nome de arquivo novo para cada exportação ou backup. Para atualizar uma cópia de trabalho existente, faça o backup, baixe a atualização do repositório e execute `python -X utf8 acervo.py importar`. A reimportação dos PDFs requer `pdftotext` do Poppler no `PATH` e preserva os registros cadastrados na cópia local.

Para registrar uma conferência oficial, consulte a via no Busca CEP e use `python -X utf8 acervo.py registrar-conferencia --help`. Guarde o ID da observação postal, a data e a referência da consulta. [Busca CEP dos Correios](https://buscacepinter.correios.com.br/app/endereco/index.php)

## Integração com o cartório

| Saída | Uso |
| --- | --- |
| **SQLite `consulta_v1`** | Visão de leitura com os dados publicados e seu estado. Use `trecho_id` para referenciar a correspondência e `equivalencia_trecho` para consultar vínculos documentados. |
| **JSON do comando `consultar`** | Inclui `versao`, `criterio` e `resultados`. Cada resultado pode trazer `historico_nomes`, `observacoes_postais` e `mudancas_cadastradas`. |
| **CSV** | Exportação das informações de consulta para planilha, com nomes anteriores documentados nos atos importados. |

`referencia_postal` é a data ou o mês da fonte. `abrangencia_fonte_postal` identifica listas integrais e boletins complementares. `divergencia_postal` sinaliza diferenças entre observações, inclusive entre edições. Confira as datas e páginas antes de interpretar uma divergência como conflito na lista mais recente. `conferencia_correios` se refere à observação postal indicada no resultado. [Plano de integração](PLANO.md#4-integração-com-o-cartório)

## Contribuir

Encontrou um nome antigo, uma lei, uma diferença de grafia ou um CEP diferente? Envie uma sugestão com **nome do logradouro, bairro, trecho, data e fonte pública** quando disponíveis. Informe qual informação está em dúvida. A issue ficará pública, então use apenas dados necessários para identificar o logradouro. [Relatar uma informação de logradouro](https://github.com/KayssonGabriel/acervo-logradouros-morrinhos-go/issues/new?template=informacao-logradouro.yml)

Para preparar uma contribuição de dados ou código, siga o [guia de manutenção e validação](AGENTS.md). O Git inclui o código, as fontes públicas e a base inicial gerada. Mantenha bancos de trabalho, conferências, backups, credenciais e arquivos brutos do IBGE na sua pasta local. Ao propor uma alteração na base, indique a fonte, o artigo ou a página e o que ainda precisa de verificação.
