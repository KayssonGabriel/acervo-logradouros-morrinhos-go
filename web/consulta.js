'use strict';

const porId = (id) => document.getElementById(id);
const formulario = porId('busca');
const lista = porId('lista');
const detalhe = porId('detalhe');
const contador = porId('contador');
const mensagem = porId('mensagem');
const avisoConsulta = porId('aviso-consulta');
const filtroPendencia = porId('pendencia-cep');
const campoBusca = porId('termo');
const abas = [porId('tab-nomes'), porId('tab-ceps')];
const paginaAnterior = porId('anterior');
const paginaProxima = porId('proxima');
const formatoNumero = new Intl.NumberFormat('pt-BR');
let pedido;
let filtro;
let pagina = 1;
let fontesCarregadas = false;
let edicaoHabilitada = false;
let trechoSelecionado;
const dialogoMudanca = porId('dialogo-mudanca');
const formMudanca = porId('form-mudanca');
const situacaoCep = formMudanca.elements.situacao_cep;
const cepAnterior = formMudanca.elements.cep_anterior;
const cepNovo = formMudanca.elements.cep_novo;
const salvarMudanca = porId('salvar-mudanca');

const situacoes = {
  pendente: 'Conferência pendente', confirmado: 'Conferido nos Correios',
  divergente: 'Conferência divergente', nao_localizado: 'CEP não localizado',
};
const historicos = {
  historico_a_confirmar: 'A confirmar', alteracao_documentada: 'Mudança documentada',
  denominacao_documentada: 'Nome documentado', cep_geral_historico: 'CEP geral histórico',
};
const pendenciasCep = {
  sem_cep_atual: 'Trechos sem CEP identificado nas fontes oficiais atuais.',
  cadastro_a_confirmar: 'O trecho está sem CEP atual e sem CEP específico lançado, ou o último cadastro deixou o CEP a confirmar.',
  correios_a_conferir: 'O CEP consta da lista atual ou complementar. A conferência nos Correios está pendente ou precisa de revisão.',
};

function elemento(tag, texto, classe) {
  const no = document.createElement(tag);
  if (texto) no.textContent = texto;
  if (classe) no.className = classe;
  return no;
}

function icone(tipo) {
  const namespace = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(namespace, 'svg');
  const use = document.createElementNS(namespace, 'use');
  svg.setAttribute('aria-hidden', 'true');
  use.setAttribute('href', `/icones.svg#${tipo}`);
  svg.append(use);
  return svg;
}

function dataFormatada(data) {
  return data ? data.split('-').reverse().join('/') : 'A confirmar';
}

function documento(titulo, textos, fonte, rotulo = 'Abrir fonte') {
  const linha = elemento('div', null, 'registro');
  const corpo = elemento('div');
  corpo.append(elemento('strong', titulo));
  for (const texto of textos.filter(Boolean)) corpo.append(elemento('p', texto));
  const fichas = [
    [fonte.ficha_prefeitura, fonte.ficha_prefeitura?.endsWith('.pdf') ? 'PDF da Prefeitura' : 'Ficha da Prefeitura'],
    [fonte.ficha_camara, 'Ficha da Câmara'],
  ];
  for (const [urlFicha, tituloFicha] of fichas) {
    if (!urlFicha) continue;
    const ficha = elemento('a', tituloFicha);
    ficha.href = urlFicha;
    ficha.target = '_blank';
    ficha.rel = 'noopener noreferrer';
    const paragrafo = elemento('p');
    paragrafo.append(ficha);
    corpo.append(paragrafo);
  }
  linha.append(icone('arquivo'), corpo);
  if (fonte.url) {
    let rotuloFonte = rotulo;
    if (fonte.pdf_prefeitura_assinado) rotuloFonte = 'Abrir versão assinada';
    else if (fonte.pdf_camara_assinado) rotuloFonte = 'Abrir versão assinada da Câmara';
    else if (fonte.pdf_prefeitura_assinado === false) rotuloFonte = 'Consultar exemplar disponível';
    const link = elemento('a', rotuloFonte);
    let url;
    try { url = new URL(fonte.url, location.origin); } catch { return linha; }
    if (url.protocol === 'https:' || (url.origin === location.origin && url.pathname.startsWith('/fontes/leis/'))) {
      if (fonte.pagina && url.pathname.toLowerCase().endsWith('.pdf')) url.hash = `page=${fonte.pagina}`;
      link.href = url.href;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.setAttribute('aria-label', `${rotuloFonte} · ${titulo} (nova aba)`);
      link.append(icone('externo'));
      linha.append(link);
    }
  }
  return linha;
}

function escolherAba(ativa) {
  for (const aba of abas) {
    const selecionada = aba === ativa;
    aba.setAttribute('aria-selected', String(selecionada));
    aba.tabIndex = selecionada ? 0 : -1;
    porId(aba.getAttribute('aria-controls')).hidden = !selecionada;
  }
}

for (const aba of abas) {
  aba.addEventListener('click', () => escolherAba(aba));
  aba.addEventListener('keydown', (evento) => {
    const outra = aba === abas[0] ? 1 : 0;
    const destinos = {ArrowLeft: outra, ArrowRight: outra, Home: 0, End: 1};
    if (!Object.hasOwn(destinos, evento.key)) return;
    evento.preventDefault();
    const destino = abas[destinos[evento.key]];
    escolherAba(destino);
    destino.focus();
  });
}

function nome(trecho) {
  return trecho.nome_municipal_documentado || trecho.nome_postal_publicado || 'Logradouro';
}

function descricaoNomePostal(trecho) {
  const legal = trecho.nome_municipal_documentado;
  const postal = trecho.nome_postal_publicado;
  if (!legal || !postal || legal.localeCompare(postal, 'pt-BR', {sensitivity: 'accent'}) === 0) return '';
  const origem = trecho.nome_postal_nos_correios ? 'Nos Correios' : 'Na lista postal';
  return `${origem}: ${postal}`;
}

function nomesHistoricosDoResultado(trecho) {
  const chave = (valor) => valor.normalize('NFC').toLocaleLowerCase('pt-BR');
  const vistos = new Set([trecho.nome_postal_publicado, trecho.nome_municipal_documentado].filter(Boolean).map(chave));
  const nomes = [
    ...(trecho.nomes_historicos || []).map((registro) => registro.nome),
    ...trecho.historico_nomes.flatMap((ato) => [ato.nome_anterior, ato.nome_atribuido]),
    ...(trecho.mudancas_cadastradas || []).map((mudanca) => mudanca.nome_anterior),
  ];
  return nomes.filter((valor) => {
    if (!valor || vistos.has(chave(valor))) return false;
    vistos.add(chave(valor));
    return true;
  });
}

function descricaoVariantes(trecho) {
  return trecho.variantes_postais?.length
    ? `Nas listas municipais anteriores: ${trecho.variantes_postais.join(' · ')}`
    : '';
}

function exibirHistorico(trecho) {
  const atos = trecho.historico_nomes.map((ato) => ({
    data: ato.data_ato,
    rotulo: 'Data do ato municipal',
    registro: documento(
      ato.nome_anterior ? `${ato.nome_anterior} → ${ato.nome_atribuido}` : ato.nome_atribuido,
      [`Lei nº ${ato.numero} · Art. ${ato.artigo}`, ato.bairro_no_ato, ato.trecho_no_ato,
        ato.data_publicacao && `Publicação em ${dataFormatada(ato.data_publicacao)}`,
        ato.vigencia_desde && `Vigência desde ${dataFormatada(ato.vigencia_desde)}`, ato.nota], ato, 'Abrir lei',
    ),
  }));
  const usos = (trecho.nomes_historicos || []).map((registro) => {
    const paginas = [`Registro do nome na p. ${registro.pagina}`];
    if (registro.pagina_correspondencia !== registro.pagina) paginas.push(`Correspondência na p. ${registro.pagina_correspondencia}`);
    return {
      data: registro.ano ? String(registro.ano) : null,
      rotulo: registro.ano ? 'Ano de uso registrado em fonte histórica' : 'Uso registrado em fonte histórica',
      registro: documento(registro.nome, [paginas.join(' · '), registro.fonte, registro.nota],
        {url: registro.url, pagina: registro.pagina_correspondencia}),
    };
  });
  const mudancas = (trecho.mudancas_cadastradas || []).map((mudanca) => {
    const anterior = mudanca.cep_anterior || 'a confirmar';
    const ceps = {
      alterado: `CEP ${anterior} → ${mudanca.cep_novo || 'a confirmar'}`,
      mantido: `CEP mantido em ${mudanca.cep_anterior}`,
      desconhecido: mudanca.cep_anterior ? `Novo CEP a confirmar · CEP anterior ${anterior}` : 'CEP a confirmar',
    };
    const titulo = mudanca.nome_anterior ? `${mudanca.nome_anterior} → ${mudanca.nome_novo}` : mudanca.nome_novo;
    return {
      data: mudanca.vigencia_desde,
      rotulo: 'Vigência da mudança cadastrada',
      registro: documento(titulo || 'Mudança de CEP', [(mudanca.cep_anterior || mudanca.cep_novo) && ceps[mudanca.situacao_cep], mudanca.fonte],
        {url: mudanca.url_fonte}),
    };
  });
  const eventos = [...atos, ...usos, ...mudancas];
  const painel = porId('painel-nomes');
  if (!eventos.length) {
    painel.replaceChildren(elemento('p', 'Histórico de nomes a confirmar nas fontes municipais.', 'vazio'));
    return false;
  }
  eventos.sort((a, b) => a.data && b.data ? a.data.localeCompare(b.data) : Number(!a.data) - Number(!b.data));
  const linhaDoTempo = elemento('ol', null, 'linha-tempo');
  linhaDoTempo.setAttribute('role', 'list');
  for (const {data, rotulo, registro} of eventos) {
    const item = elemento('li', null, 'evento-historico');
    const cabecalho = elemento('p', null, 'data-historico');
    cabecalho.append(elemento('strong', data ? dataFormatada(data) : 'Data a confirmar'), elemento('span', rotulo));
    item.append(cabecalho, registro);
    linhaDoTempo.append(item);
  }
  painel.replaceChildren(linhaDoTempo);
  return true;
}

function exibirTrecho(trecho, botao, interacao) {
  trechoSelecionado = trecho;
  porId('estado-mudanca').textContent = '';
  porId('cadastrar-mudanca').hidden = !edicaoHabilitada || trecho.situacao_postal === 'cep_geral_historico';
  mensagem.hidden = true;
  for (const item of lista.querySelectorAll('button')) {
    item.setAttribute('aria-pressed', String(item === botao));
  }
  porId('nome-via').textContent = nome(trecho);
  const postal = porId('nome-postal');
  postal.textContent = descricaoNomePostal(trecho);
  postal.hidden = !postal.textContent;
  const variante = porId('variante-postal');
  variante.textContent = descricaoVariantes(trecho);
  variante.hidden = !variante.textContent;
  porId('local-via').querySelector('span').textContent = [trecho.bairro, 'Morrinhos (GO)'].filter(Boolean).join(', ');
  porId('cep-via').textContent = trecho.cep_publicado || 'A confirmar';
  porId('referencia-via').textContent = dataFormatada(trecho.referencia_postal);
  const nomesHistoricos = trecho.nomes_historicos || [];
  const historicoEmFonte = trecho.situacao_historico === 'historico_a_confirmar' && nomesHistoricos.length;
  porId('historico-via').textContent = historicoEmFonte ? 'Nome em fonte histórica' : (historicos[trecho.situacao_historico] || 'A confirmar');

  const status = porId('status-postal');
  status.dataset.estado = trecho.conferencia_correios;
  status.textContent = situacoes[trecho.conferencia_correios] || situacoes.pendente;
  if (trecho.conferido_em) status.textContent += ` · ${dataFormatada(trecho.conferido_em)}`;
  let avisoPostal = '';
  if (trecho.situacao_postal === 'cep_geral_historico') {
    avisoPostal = 'CEP geral histórico. Informe o nome da via e o bairro para procurar um CEP específico.';
  } else if (trecho.divergencia_postal) {
    avisoPostal = 'Há outra observação com este CEP. Confira o bairro, o trecho e as fontes antes de usar o resultado.';
  } else if (trecho.situacao_postal === 'publicado_lista_anterior') {
    avisoPostal = 'Registro encontrado em uma edição anterior da lista postal.';
  }
  const situacaoVia = porId('situacao-via');
  situacaoVia.textContent = avisoPostal;
  const divergencias = trecho.ceps_municipais_divergentes || [];
  for (const fonte of divergencias) {
    if (situacaoVia.hasChildNodes()) situacaoVia.append(document.createElement('br'));
    situacaoVia.append(`A lista mais recente da Prefeitura (${dataFormatada(fonte.referencia)}) informa ${fonte.cep}. O CEP confirmado nos Correios é ${trecho.cep_publicado}. `);
    if (fonte.url) {
      const link = elemento('a', `Lista da Prefeitura, página ${fonte.pagina}`);
      link.href = `${fonte.url}#page=${fonte.pagina}`;
      link.target = '_blank';
      link.rel = 'noopener';
      situacaoVia.append(link);
    }
  }
  situacaoVia.hidden = !situacaoVia.hasChildNodes();
  porId('trecho-via').textContent = trecho.trecho_documentado || '';
  porId('trecho-via').hidden = !trecho.trecho_documentado;

  const temHistorico = exibirHistorico(trecho);
  const fontes = [];
  const anteriores = [];
  for (const fonte of trecho.observacoes_postais) {
    const mesmaGrafia = fonte.nome_original === trecho.nome_postal_publicado && fonte.bairro_original === trecho.bairro;
    const referencia = [dataFormatada(fonte.referencia), fonte.pagina && `Página ${fonte.pagina}`].filter(Boolean).join(' · ');
    const listaFonte = fonte.referencia === trecho.referencia_postal ? fontes : anteriores;
    listaFonte.push(documento(fonte.titulo, [referencia, !mesmaGrafia && [fonte.nome_original, fonte.bairro_original, fonte.cep].filter(Boolean).join(' · ')], fonte));
  }
  if (anteriores.length) {
    const arquivo = elemento('details', null, 'fontes-anteriores');
    arquivo.append(elemento('summary', `Fontes de edições anteriores (${anteriores.length})`), ...anteriores);
    fontes.push(arquivo);
  }
  porId('painel-ceps').replaceChildren(...(fontes.length ? fontes : [elemento('p', 'CEP a confirmar. A denominação está disponível no histórico.', 'vazio')]));
  escolherAba(temHistorico ? abas[0] : abas[1]);
  detalhe.hidden = false;
  if (interacao && matchMedia('(max-width: 785px)').matches) {
    detalhe.scrollIntoView({block: 'start'});
    porId('nome-via').focus({preventScroll: true});
  }
}

function mostrarMensagem(titulo, texto) {
  mensagem.replaceChildren(elemento('strong', titulo), elemento('p', texto));
  mensagem.hidden = false;
}

async function buscar(novaPagina = 1, moverFoco = false, selecionarId = null) {
  pedido?.abort();
  const atual = new AbortController();
  pedido = atual;
  mensagem.hidden = true;
  avisoConsulta.hidden = true;
  detalhe.hidden = true;
  porId('estado-mudanca').textContent = '';
  lista.replaceChildren();
  contador.textContent = 'Buscando…';
  lista.setAttribute('aria-busy', 'true');
  porId('paginacao').hidden = true;
  try {
    const parametros = new URLSearchParams({...filtro, pagina: String(novaPagina)});
    const resposta = await fetch(`/api/consulta?${parametros}`, {signal: atual.signal});
    const dados = await resposta.json();
    if (atual.signal.aborted) return;
    if (!resposta.ok) throw new Error(dados.erro || 'Não foi possível consultar a base.');
    edicaoHabilitada = dados.edicao_habilitada;
    pagina = dados.pagina;
    if (dados.total && !dados.resultados.length && novaPagina > 1) {
      return buscar(Math.ceil(dados.total / dados.por_pagina), moverFoco, selecionarId);
    }
    const aproximada = dados.criterio === 'aproximada';
    const rotulo = aproximada ? (dados.total === 1 ? 'sugestão' : 'sugestões') : (dados.total === 1 ? 'encontrado' : 'encontrados');
    contador.textContent = `${formatoNumero.format(dados.total)} ${rotulo}`;
    const avisos = [pendenciasCep[filtro.pendencia_cep]];
    if (dados.cep_geral_informado) avisos.push('O CEP geral antigo foi usado como contexto. A busca considera o nome da via e o bairro.');
    if (avisos.some(Boolean)) {
      avisoConsulta.textContent = avisos.filter(Boolean).join(' ');
      avisoConsulta.hidden = false;
    }
    if (!dados.resultados.length) {
      if (dados.conflito_entrada) {
        mostrarMensagem('Dados da busca incompatíveis', 'Confira os CEPs, o bairro e a localidade informados. O acervo é de Morrinhos (GO).');
      } else if (filtro.pendencia_cep) {
        mostrarMensagem('Nenhuma pendência com esses filtros', 'Altere o bairro ou remova o nome para ampliar a lista.');
      } else {
        mostrarMensagem('Nenhuma correspondência encontrada', 'Confira o bairro ou tente buscar por parte do nome ou pelo CEP.');
      }
      return;
    }
    let selecionado;
    for (const trecho of dados.resultados) {
      const item = elemento('li');
      const botao = elemento('button', null, 'resultado');
      const rotulo = elemento('span');
      botao.type = 'button';
      botao.setAttribute('aria-pressed', 'false');
      botao.setAttribute('aria-controls', 'detalhe');
      const cep = trecho.cep_publicado || 'CEP a confirmar';
      const aviso = filtro.pendencia_cep === 'sem_cep_atual' && trecho.cep_publicado ? 'Lista anterior' : null;
      rotulo.append(elemento('strong', nome(trecho)));
      const postal = descricaoNomePostal(trecho);
      if (postal) rotulo.append(elemento('small', postal));
      const variante = descricaoVariantes(trecho);
      if (variante) rotulo.append(elemento('small', variante));
      const nomesHistoricos = nomesHistoricosDoResultado(trecho);
      if (nomesHistoricos.length) {
        const titulo = nomesHistoricos.length === 1 ? 'Nome histórico' : 'Nomes históricos';
        rotulo.append(elemento('small', `${titulo} — ${nomesHistoricos.join(' · ')}`, 'resultado-historico'));
      }
      rotulo.append(elemento('small', [trecho.bairro, cep, aviso].filter(Boolean).join(' · ')));
      botao.append(icone('pin'), rotulo, icone('direita'));
      botao.addEventListener('click', () => exibirTrecho(trecho, botao, true));
      if (trecho.trecho_id === selecionarId) selecionado = {trecho, botao};
      item.append(botao);
      lista.append(item);
    }
    const primeiro = lista.querySelector('button');
    if (selecionado) {
      exibirTrecho(selecionado.trecho, selecionado.botao, false);
    } else if (aproximada) {
      mostrarMensagem('Sugestões por grafia semelhante', 'Selecione uma sugestão para conferir o nome, o bairro e as fontes. A semelhança não confirma que se trata da mesma via.');
    } else {
      exibirTrecho(dados.resultados[0], primeiro, false);
    }
    if (moverFoco) primeiro.focus();
    const totalPaginas = Math.ceil(dados.total / dados.por_pagina);
    porId('paginacao').hidden = totalPaginas < 2;
    porId('pagina-atual').textContent = `Página ${pagina} de ${totalPaginas}`;
    paginaAnterior.disabled = pagina <= 1;
    paginaProxima.disabled = pagina >= totalPaginas;
  } catch (erro) {
    if (atual.signal.aborted) return;
    contador.textContent = 'Consulta indisponível';
    mostrarMensagem('Não foi possível concluir a consulta', erro instanceof TypeError ? 'Verifique se o acervo local está aberto e tente novamente.' : erro.message);
  } finally {
    if (pedido === atual) lista.setAttribute('aria-busy', 'false');
  }
}

function enviarBusca() {
  filtro = {q: campoBusca.value.trim(), bairro: porId('bairro').value, pendencia_cep: filtroPendencia.value};
  if (filtro.q || filtro.pendencia_cep) buscar();
}

function atualizarObrigatoriedadeBusca() {
  campoBusca.required = !filtroPendencia.value;
}

filtroPendencia.addEventListener('change', atualizarObrigatoriedadeBusca);
formulario.addEventListener('submit', (evento) => {
  evento.preventDefault();
  enviarBusca();
});
paginaAnterior.addEventListener('click', () => buscar(pagina - 1, true));
paginaProxima.addEventListener('click', () => buscar(pagina + 1, true));

function atualizarCamposCep() {
  const mantido = situacaoCep.value === 'mantido';
  const alterado = situacaoCep.value === 'alterado';
  cepAnterior.disabled = !situacaoCep.value;
  cepAnterior.required = mantido;
  porId('rotulo-cep-anterior').hidden = cepAnterior.disabled;
  porId('texto-cep-anterior').textContent = mantido ? 'CEP que continuou igual' : 'CEP anterior, se conhecido';
  cepNovo.disabled = !alterado;
  cepNovo.required = alterado;
  porId('rotulo-cep-novo').hidden = !alterado;
}

situacaoCep.addEventListener('change', atualizarCamposCep);
porId('cadastrar-mudanca').addEventListener('click', () => {
  formMudanca.reset();
  cepAnterior.value = trechoSelecionado.cep_publicado || '';
  porId('erro-mudanca').hidden = true;
  porId('trecho-mudanca').textContent = [nome(trechoSelecionado), trechoSelecionado.bairro].filter(Boolean).join(' · ');
  atualizarCamposCep();
  dialogoMudanca.showModal();
});
porId('cancelar-mudanca').addEventListener('click', () => dialogoMudanca.close());
dialogoMudanca.addEventListener('cancel', (evento) => {
  if (salvarMudanca.disabled) evento.preventDefault();
});
formMudanca.addEventListener('submit', async (evento) => {
  evento.preventDefault();
  if (salvarMudanca.disabled) return;
  const trechoId = trechoSelecionado.trecho_id;
  const dados = {...Object.fromEntries(new FormData(formMudanca)), trecho_id: trechoId};
  const erro = porId('erro-mudanca');
  erro.hidden = true;
  salvarMudanca.disabled = porId('cancelar-mudanca').disabled = true;
  try {
    const resposta = await fetch('/api/mudancas', {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(dados),
    });
    const resultado = await resposta.json();
    if (!resposta.ok) throw new Error(resultado.erro);
    dialogoMudanca.close();
    await buscar(pagina, false, trechoId);
    porId('estado-mudanca').textContent = resultado.criado ? 'Mudança cadastrada.' : 'Esta mudança já estava cadastrada.';
    if (!detalhe.hidden && trechoSelecionado.trecho_id === trechoId) porId('nome-via').focus();
    else filtroPendencia.focus();
  } catch (falha) {
    erro.textContent = falha instanceof TypeError ? 'Não foi possível conectar ao acervo local.' : falha.message;
    erro.hidden = false;
  } finally {
    salvarMudanca.disabled = porId('cancelar-mudanca').disabled = false;
  }
});

async function bairrosDisponiveis() {
  try {
    const resposta = await fetch('/api/bairros');
    if (!resposta.ok) return;
    const {bairros} = await resposta.json();
    porId('bairro').append(...bairros.map((bairro) => new Option(bairro, bairro)));
  } catch {
    // A busca textual também aceita o bairro após uma vírgula.
  }
}

async function listarFontes() {
  if (fontesCarregadas) return;
  const estado = porId('estado-fontes');
  estado.textContent = 'Carregando fontes…';
  try {
    const resposta = await fetch('/api/fontes');
    if (!resposta.ok) throw new Error();
    const {fontes} = await resposta.json();
    const grupos = [['lista_postal', 'Listas postais'], ['lei_municipal', 'Legislação municipal'], ['comunicado', 'Comunicados']];
    porId('grupos-fontes').replaceChildren(...grupos.map(([tipo, titulo]) => {
      const grupo = elemento('section', null, 'grupo-fontes');
      grupo.append(elemento('h2', titulo));
      for (const fonte of fontes.filter((item) => item.tipo === tipo)) {
        grupo.append(documento(fonte.titulo, [dataFormatada(fonte.referencia)], fonte));
      }
      return grupo;
    }));
    estado.textContent = '';
    fontesCarregadas = true;
  } catch {
    estado.textContent = 'As fontes estão indisponíveis. Volte à consulta e tente novamente.';
  }
}

function navegar(focar = false) {
  const fontes = location.hash === '#fontes';
  porId('tela-consulta').hidden = fontes;
  porId('tela-fontes').hidden = !fontes;
  porId(fontes ? 'nav-fontes' : 'nav-consulta').setAttribute('aria-current', 'page');
  porId(fontes ? 'nav-consulta' : 'nav-fontes').removeAttribute('aria-current');
  if (fontes) listarFontes();
  if (focar && fontes) porId('titulo-fontes').focus();
}

window.addEventListener('hashchange', () => navegar(true));
navegar();
bairrosDisponiveis();
atualizarObrigatoriedadeBusca();
enviarBusca();
