# Plano do acervo de Morrinhos (GO)

Revisão de 24/11/2026. O acervo serve para identificar o endereço de uma via citada em documento antigo. A resposta deve indicar o trecho, os nomes documentados, os CEPs observados e as respectivas fontes. Os estados «publicado em lista», «denominação comprovada em ato» e «conferido nos Correios» respondem a perguntas diferentes.

## 1. Pesquisa e cobertura

- Use o bairro, a via e o trecho como unidade de pesquisa. Preserve grafia, data de referência, página e limites de cada observação. Registre faixa de numeração ou lado da via quando a fonte trouxer essa informação. Uma data de publicação da lista postal serve para ordenar observações. A vigência exige evidência própria.
- Compare a lista postal com o cadastro municipal de vias para localizar logradouros ainda sem CEP identificado, mudanças de bairro e trechos com numeração distinta. Pesquise a lei de denominação de cada via no portal da Prefeitura e da Câmara. Quando houver duplicidade, use o mapa e a descrição legal para decidir quais registros correspondem ao mesmo trecho.
- A Lei municipal nº 3.091/2014 prevê, em seu art. 27, a comunicação de mudanças de nome de logradouro e de numeração ao Registro Geral de Imóveis. Vale localizar essas comunicações no acervo do cartório. Para complementar a pesquisa, o art. 22 descreve informações que a Prefeitura comunica aos Correios, incluindo o número da lei de denominação e a fronteira entre bairros. Registre no acervo apenas a informação pública necessária do logradouro. [Legislação municipal](https://leis.morrinhos.go.leg.br/leis) · [Lei nº 3.091/2014](fontes/leis/lei-3091-2014.pdf) · [Mapa da cidade](https://morrinhos.go.gov.br/mapa-da-cidade-de-morrinhos/)
- Faça a conferência postal com a resposta direta do Busca CEP ou com a edição oficial do DNE disponível ao cartório. Registre data, responsável, resultado e evidência. Acompanhe por bairro os registros com histórico a confirmar, os vínculos em conflito e os CEPs ainda sem conferência. [Busca CEP](https://buscacepinter.correios.com.br/app/endereco/index.php) · [DNE, Correios](https://www.correios.com.br/enviar/precisa-de-ajuda/guia-de-enderecamento/guia-de-enderecamento)

## 2. Segurança e manutenção da base

- Permissões de pasta do Windows controlam quem pode importar, editar o catálogo e registrar conferências. Disponibilize uma cópia de consulta ou um serviço interno somente leitura para os demais usuários. Preserve a origem dos PDFs, seu hash, a lei que sustenta cada equivalência e os vínculos anteriores nas cópias de segurança.
- Valide novos PDFs e metadados antes da transação de escrita. Reaproveite fontes já importadas quando o conteúdo e os metadados coincidirem. Aplique uma edição nova sob seu próprio ID. Revise de forma transacional as equivalências vinculadas a um ato quando sua interpretação for corrigida.
- Antes de importações importantes ou migrações, gere um backup consistente do SQLite e arquive o catálogo e os PDFs correspondentes. Teste uma consulta na cópia e guarde-a no local de backup institucional apropriado. A reimportação repõe o conteúdo das fontes. A restauração do banco preserva também os registros de conferência e seus IDs.
- O CSV é uma saída para uso humano. A publicação é feita após terminar a escrita, e células que o Excel poderia interpretar como fórmulas são tratadas como texto. Os valores canônicos ficam no banco e na saída JSON local.

## 3. Desempenho e evolução

- A busca reúne candidatos por nome, CEP e bairro no banco e usa os índices de observações para recuperar os históricos. Meça separadamente a mediana de uma consulta por CEP, de um nome com bairro e de uma busca ampla com a base real. Repita a medição após cada lote significativo. Se um consumidor precisar de buscas amplas pela rede, defina paginação e limites com a equipe do sistema.
- SQLite atende à versão local. Se a operação exigir edição concorrente em vários computadores, avalie um banco em servidor e migre após testar a preservação dos IDs e da trilha de fontes. [Orientação do SQLite sobre uso local e rede](https://www.sqlite.org/whentouse.html)

## 4. Integração com o cartório

- A integração começa em leitura. Combine o formato aceito pelo sistema e os campos que ele pode consumir. Use `trecho_id` como referência estável e mantenha as equivalências consultáveis. IDs numéricos de observação servem à manutenção local e dependem da cópia do banco.
- Uma futura API interna deve autenticar as contas de serviço, usar conexão protegida e devolver uma lista explícita de campos adequados ao consumidor. Separe a referência interna de conferência e o nome do responsável da saída de integração. Evite registrar em logs dados de matrículas, partes ou endereços particulares recebidos como contexto de pesquisa.
- Retorne todas as correspondências plausíveis com suas fontes. Destaque se a consulta encontrou um nome ou CEP histórico e qual observação fundamenta a correspondência. O sistema do cartório pode apresentar a indicação à equipe. Alterações em registros cartorários exigem o fluxo do próprio sistema.
- Antes de liberar a integração, valide casos de homônimos, renomeações parciais, fontes conflitantes, CEP geral antigo, recuperação de backup e consultas feitas por perfis de acesso diferentes. O ambiente do fornecedor do cartório e a conferência oficial de cada CEP ainda estão pendentes.
