'use strict';

const porId = (id) => document.getElementById(id);
const formulario = porId('busca');
const lista = porId('lista');
const detalhe = porId('detalhe');
const contador = porId('contador');
const mensagem = porId('mensagem');
const avisoConsulta = porId('aviso-consulta');
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
    let url;
    try { url = new URL(fonte.url); } catch { return linha; }
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
  trechoSelecionado = trecho;
  porId('estado-mudanca').textContent = '';
  porId('cadastrar-mudanca').hidden = !edicaoHabilitada || trecho.situacao_postal === 'cep_geral_historico';
  mensagem.hidden = true;
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

  const mudancas = (trecho.mudancas_cadastradas || []).map((mudanca) => {
    const anterior = mudanca.cep_anterior || 'a confirmar';
    const ceps = {
      alterado: `CEP ${anterior} → ${mudanca.cep_novo}`,
      mantido: `CEP mantido: ${mudanca.cep_anterior}`,
      desconhecido: mudanca.cep_anterior ? `Novo CEP a confirmar · CEP anterior ${anterior}` : 'CEP a confirmar',
    };
    const titulo = mudanca.nome_anterior ? `${mudanca.nome_anterior} → ${mudanca.nome_novo}` : mudanca.nome_novo;
    return documento(
      titulo || 'Mudança de CEP',
      [ceps[mudanca.situacao_cep], `Vigência: ${dataFormatada(mudanca.vigencia_desde)}`, mudanca.fonte],
      {url: mudanca.url_fonte},
    );
  });
  porId('historico-mudancas').replaceChildren(...mudancas);
  porId('mudancas-via').hidden = !mudancas.length;

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

async function buscar(novaPagina = 1, moverFoco = false, selecionarId = null) {
  pedido?.abort();
  const atual = new AbortController();
  pedido = atual;
  mensagem.hidden = true;
  avisoConsulta.hidden = true;
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
    edicaoHabilitada = dados.edicao_habilitada;
    pagina = dados.pagina;
    const aproximada = dados.criterio === 'aproximada';
    const rotulo = aproximada ? (dados.total === 1 ? 'sugestão' : 'sugestões') : (dados.total === 1 ? 'encontrado' : 'encontrados');
    contador.textContent = `${formatoNumero.format(dados.total)} ${rotulo}`;
    if (dados.cep_geral_informado) {
      avisoConsulta.textContent = 'O CEP geral antigo foi usado como contexto. A busca considera o nome da via e o bairro.';
      avisoConsulta.hidden = false;
    }
    if (!dados.resultados.length) {
      if (dados.conflito_entrada) {
        mostrarMensagem('Dados da busca incompatíveis', 'Confira os CEPs, o bairro e a localidade informados. O acervo é de Morrinhos (GO).');
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
      rotulo.append(elemento('strong', nome(trecho)), elemento('small', [trecho.bairro, trecho.cep_publicado || 'CEP a confirmar'].filter(Boolean).join(' · ')));
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
  filtro = {q: porId('termo').value.trim(), bairro: porId('bairro').value};
  if (filtro.q) buscar();
}

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
    if (!detalhe.hidden) porId('nome-via').focus();
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
enviarBusca();
