# Acervo de logradouros e CEPs de Morrinhos (GO)

O banco SQLite reúne nomes, trechos, CEPs e fontes públicas de Morrinhos, Goiás. O arquivo `morrinhos.csv` permite abrir o cadastro no Excel e filtrar por bairro, pelo nome postal ou pelos nomes anteriores documentados. A versão de dezembro de 2025 contém 1.021 registros postais. A pesquisa histórica e a conferência nos Correios são registradas progressivamente.

Para ampliar a pesquisa, fazer ajustes ou pedir a revisão de outra IA, use [AGENTS.md](AGENTS.md). O roteiro inclui as fontes oficiais, os critérios de evidência e os casos de teste.

## Consultar

Para abrir a interface local no navegador, inicie o servidor na pasta do acervo.

```powershell
python -X utf8 interface.py
```

Acesse [a consulta local](http://127.0.0.1:8765). A tela é adaptável a computador e celular, com busca por nome ou CEP, filtro por bairro e acesso às fontes oficiais. O servidor escuta apenas no próprio computador e usa o SQLite em modo somente leitura.

No PowerShell, a partir da pasta do acervo, use Python 3.10 ou superior. A consulta e a exportação usam o banco existente. A importação dos PDFs requer o `pdftotext` do Poppler no PATH.

Em um clone novo do repositório, gere primeiro a base local e o CSV. O Git guarda o código, o catálogo e os PDFs públicos usados na importação. O banco de trabalho, os CSVs gerados e os backups ficam na pasta local. Depois da importação, inicie a interface ou use os comandos de consulta.

```powershell
python -X utf8 acervo.py importar
python -X utf8 acervo.py exportar 'morrinhos.csv'
```

```powershell
python -X utf8 acervo.py consultar 'Rua 03' --bairro 'Jardim América'
python -X utf8 acervo.py consultar 'Avenida Central' --bairro 'Setor Monte Verde'
python -X utf8 acervo.py consultar 'Av. Central, Setor Monte Verde'
python -X utf8 acervo.py consultar '75654-069'
python -X utf8 acervo.py consultar 'R. 03, nº 44, Jardim América, Morrinhos - GO, CEP 75.650-281'
python -X utf8 auditar_acervo.py
python -X utf8 acervo.py exportar 'morrinhos-revisao.csv'
```

A busca aceita nomes com ou sem acentos, abreviações, formatos comuns de CEP e bairro no final do texto. Em endereços copiados, complementos explícitos como número predial e quadra servem de contexto. Quando a busca textual não encontra resultados, também tenta palavras fora de ordem, prefixos e grafias próximas. A interface marca as grafias próximas como sugestões e pede que você escolha uma para conferir a fonte. O bairro e o CEP específico informado continuam restringindo os resultados.

O JSON traz o nome municipal documentado, o nome postal publicado, o CEP, a situação da conferência, as fontes e o `criterio` de busca. Use `situacao_historico` para localizar os nomes ainda a pesquisar. Em `observacoes_postais`, cada entrada preserva a grafia, o bairro e o CEP tal como aparecem no documento original. Um CEP associado a registros conflitantes mantém as diferentes observações disponíveis, com `divergencia_postal`.

O indicador `divergencia_postal` abrange diferenças entre edições. Use as referências e páginas para distinguir uma diferença histórica de um conflito na publicação mais recente. A lista integral e os boletins complementares são identificados por `abrangencia_fonte_postal`.

## Atualizar

1. Mantenha os PDFs originais e uma cópia de segurança do banco. O comando `python -X utf8 acervo.py backup 'morrinhos-copia.sqlite3'` cria uma cópia consistente e checa sua integridade e as referências. Teste a cópia com `python -X utf8 acervo.py --banco 'morrinhos-copia.sqlite3' consultar '75650-281'`. O banco também guarda as conferências inseridas pela equipe.
2. Cadastre cada nova lista em [`dados/fontes.json`](dados/fontes.json) com ID próprio, arquivo, origem, referência, abrangência e quantidade de linhas a importar. Use `complementar` para boletins parciais. Os nomes de bairro e CEPs permanecem associados às fontes que os publicaram.
3. Arquive novas leis em `fontes/leis/`, registre artigo, página e trecho no [índice legislativo](LEGISLACAO.md) e acrescente o ato ao mesmo JSON. Quando houver evidência que ligue registros postais, use `vinculo_postal` para identificar o trecho principal já existente e `registros_postais_anteriores` para associar outras ocorrências. O banco conserva os IDs das ocorrências anteriores e o ato que justificou o vínculo.
4. Execute `python -X utf8 acervo.py importar`. A operação valida fontes conhecidas sem repetir a leitura postal pelo Poppler. Alterações no conteúdo ou nos metadados de uma fonte exigem um ID novo. Revise os resultados e gere um novo CSV com `exportar`, usando um nome de arquivo disponível. A exportação preserva os valores no banco e protege a abertura do CSV no Excel.

Após uma consulta direta ao Busca CEP, use `python -X utf8 acervo.py registrar-conferencia --help`. Informe o `observacao_postal_id` retornado pela busca, a data, o responsável, o resultado, o endereço retornado quando houver e a referência da evidência. O procedimento vincula a conferência à observação escolhida. [Busca CEP dos Correios](https://buscacepinter.correios.com.br/app/endereco/index.php)

## Integração com o cartório

`consulta_v1` é a visão SQLite de consulta atualizada pela [migração 002](dados/migracao-002.sql). O comando `consultar` é uma interface JSON local de leitura, com `versao: 1` e a lista `resultados`. O campo `trecho_id` é o identificador da correspondência no acervo. A tabela `equivalencia_trecho` permite localizar o ID principal de um vínculo já comprovado. Nomes, bairros e CEPs são dados de consulta e podem mudar com o tempo.

`referencia_postal` é a data ou mês de referência da fonte. A data em que um CEP entrou em vigor requer evidência própria. `nome_municipal_documentado` indica a última denominação municipal localizada no acervo. O status `conferencia_correios` informa se existe uma conferência registrada para aquela observação postal. CSV e JSON distinguem esses campos para que o sistema consumidor possa mostrar a procedência do resultado.

O banco foi preparado para uso local. O sistema do cartório pode usar a visão de leitura, o JSON ou o CSV quando o formato de integração estiver definido.

As etapas de pesquisa, os controles operacionais e os testes de integração estão no [plano revisado](PLANO.md).

## Fontes

As duas listas municipais de dezembro de 2025 contêm os mesmos registros, ordenados por nome ou bairro. As listas anteriores de novembro de 2024 e de janeiro de 2025, esta em duas ordenações, contêm as mesmas 970 observações extraídas. O banco conserva a origem de cada registro. O mapa municipal pode ajudar a investigar a continuidade de uma via e comparar seus trechos. [Listas municipais de CEP](https://morrinhos.go.gov.br/codigo-de-enderecamento-postal-cep/) · [Lista de novembro de 2024](https://morrinhos.go.gov.br/prefeitura-apresenta-cadastros-de-logradouros-de-morrinhos-com-novos-ceps/) · [Mapa municipal](https://morrinhos.go.gov.br/mapa-da-cidade-de-morrinhos/) · [Legislação da Câmara](https://leis.morrinhos.go.leg.br/leis)
