'use strict';

const porId = (id) => document.getElementById(id);
const formulario = porId('busca');
const lista = porId('lista');
const detalhe = porId('detalhe');
const contador = porId('contador');
const mensagem = porId('mensagem');
const abas = [porId('tab-nomes'), porId('tab-ceps')];
const paginaAnterior = porId('anterior');
const paginaProxima = porId('proxima');
const formatoNumero = new Intl.NumberFormat('pt-BR');
let pedido;
let filtro;
let pagina = 1;
let fontesCarregadas = false;

const situacoes = {
  pendente: 'Conferência pendente', confirmado: 'Conferido nos Correios',
  divergente: 'Conferência divergente', nao_localizado: 'CEP não localizado',
};
const historicos = {
  historico_a_confirmar: 'A confirmar', alteracao_documentada: 'Mudança documentada',
  denominacao_documentada: 'Nome documentado', cep_geral_historico: 'CEP geral histórico',
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
  linha.append(icone('arquivo'), corpo);
  if (fonte.url) {
    const link = elemento('a', rotulo);
    const url = new URL(fonte.url);
    if (url.protocol === 'https:') {
      if (fonte.pagina && url.pathname.toLowerCase().endsWith('.pdf')) url.hash = `page=${fonte.pagina}`;
      link.href = url.href;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.setAttribute('aria-label', `${rotulo} · ${titulo} (nova aba)`);
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
  return trecho.nome_postal_publicado || trecho.nome_municipal_documentado || 'Logradouro';
}

function exibirTrecho(trecho, botao, interacao) {
  for (const item of lista.querySelectorAll('button')) {
    item.setAttribute('aria-pressed', String(item === botao));
  }
  porId('nome-via').textContent = nome(trecho);
  porId('local-via').querySelector('span').textContent = [trecho.bairro, 'Morrinhos (GO)'].filter(Boolean).join(', ');
  porId('cep-via').textContent = trecho.cep_publicado || 'A confirmar';
  porId('referencia-via').textContent = dataFormatada(trecho.referencia_postal);
  porId('historico-via').textContent = historicos[trecho.situacao_historico] || 'A confirmar';

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
  porId('situacao-via').textContent = avisoPostal;
  porId('situacao-via').hidden = !avisoPostal;
  porId('trecho-via').textContent = trecho.trecho_documentado || '';
  porId('trecho-via').hidden = !trecho.trecho_documentado;

  const nomes = trecho.historico_nomes.map((ato) => documento(
    ato.nome_anterior ? `${ato.nome_anterior} → ${ato.nome_atribuido}` : ato.nome_atribuido,
    [`Lei nº ${ato.numero} · Art. ${ato.artigo} · ${dataFormatada(ato.data_ato)}`,
      ato.bairro_no_ato, ato.nota], ato, 'Abrir lei',
  ));
  const fontes = [];
  const anteriores = [];
  for (const fonte of trecho.observacoes_postais) {
    const mesmaGrafia = fonte.nome_original === nome(trecho) && fonte.bairro_original === trecho.bairro;
    const referencia = [dataFormatada(fonte.referencia), fonte.pagina && `Página ${fonte.pagina}`].filter(Boolean).join(' · ');
    const listaFonte = fonte.referencia === trecho.referencia_postal ? fontes : anteriores;
    listaFonte.push(documento(fonte.titulo, [referencia, !mesmaGrafia && [fonte.nome_original, fonte.bairro_original, fonte.cep].filter(Boolean).join(' · ')], fonte));
  }
  if (anteriores.length) {
    const arquivo = elemento('details', null, 'fontes-anteriores');
    arquivo.append(elemento('summary', `Fontes de edições anteriores (${anteriores.length})`), ...anteriores);
    fontes.push(arquivo);
  }
  porId('painel-nomes').replaceChildren(...(nomes.length ? nomes : [elemento('p', 'Histórico de nomes a confirmar nas fontes municipais.', 'vazio')]));
  porId('painel-ceps').replaceChildren(...(fontes.length ? fontes : [elemento('p', 'CEP a confirmar. A denominação está disponível no histórico.', 'vazio')]));
  escolherAba(nomes.length ? abas[0] : abas[1]);
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

async function buscar(novaPagina = 1, moverFoco = false) {
  pedido?.abort();
  const atual = new AbortController();
  pedido = atual;
  mensagem.hidden = true;
  detalhe.hidden = true;
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
    pagina = dados.pagina;
    contador.textContent = `${formatoNumero.format(dados.total)} ${dados.total === 1 ? 'encontrado' : 'encontrados'}`;
    if (!dados.resultados.length) {
      mostrarMensagem('Nenhuma correspondência encontrada', 'Confira o bairro ou tente buscar por parte do nome ou pelo CEP.');
      return;
    }
    for (const trecho of dados.resultados) {
      const item = elemento('li');
      const botao = elemento('button', null, 'resultado');
      const rotulo = elemento('span');
      botao.type = 'button';
      botao.setAttribute('aria-pressed', 'false');
      botao.setAttribute('aria-controls', 'detalhe');
      rotulo.append(elemento('strong', nome(trecho)), elemento('small', [trecho.bairro, trecho.cep_publicado || 'CEP a confirmar'].filter(Boolean).join(' · ')));
      botao.append(icone('pin'), rotulo, icone('direita'));
      botao.addEventListener('click', () => exibirTrecho(trecho, botao, true));
      item.append(botao);
      lista.append(item);
    }
    const primeiro = lista.querySelector('button');
    exibirTrecho(dados.resultados[0], primeiro, false);
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
  filtro = {q: porId('termo').value.trim(), bairro: porId('bairro').value};
  if (filtro.q) buscar();
}

formulario.addEventListener('submit', (evento) => {
  evento.preventDefault();
  enviarBusca();
});
paginaAnterior.addEventListener('click', () => buscar(pagina - 1, true));
paginaProxima.addEventListener('click', () => buscar(pagina + 1, true));

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
enviarBusca();
