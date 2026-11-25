from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache
import re
import unicodedata


ABREVIACOES = {
    'r': 'rua', 'av': 'avenida', 'al': 'alameda', 'tv': 'travessa', 'trav': 'travessa',
    'pc': 'praca', 'pca': 'praca', 'rod': 'rodovia', 'est': 'estrada',
    'dr': 'doutor', 'dra': 'doutora', 'prof': 'professor', 'profa': 'professora',
    'cel': 'coronel', 'ver': 'vereador', 'pref': 'prefeito', 'sen': 'senador', 'pe': 'padre',
}
TIPOS = {'rua', 'avenida', 'alameda', 'travessa', 'praca', 'rodovia', 'estrada', 'via', 'viela'}
PREFIXOS_BAIRRO = ('bairro', 'setor', 'vila', 'loteamento', 'residencial', 'povoado')
CEP_NO_TEXTO = re.compile(r'(?<!\w)(?:cep\b\s*[:=]?\s*)?([0-9]{2}[. ]?[0-9]{3}[- ]?[0-9]{3})(?!\w)', re.I)
LOCALIDADE = re.compile(r'\bMorrinhos(?:\s*[,/–—(-]\s*|\s+)'
                        r'(Goiás|Goias|AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO)\b\s*\)?', re.I)
COMPLEMENTO = re.compile(r'^(?:(?:n|no|numero|qd|q|quadra|lote|lt|bloco|apt|apto|apartamento)\s+[0-9].*|s\s*n|sem numero)$')
NUMERO_EXPLICITO = re.compile(r'\bn[º°]\s*\d+[a-z]?\b', re.I)


def chave(texto):
    if texto is None:
        return None
    texto = unicodedata.normalize('NFKD', texto.casefold())
    texto = ''.join(letra for letra in texto if not unicodedata.combining(letra))
    texto = ' '.join(re.findall(r'[a-z0-9]+', texto))
    return re.sub(r'\b0+(?=[0-9])', '', texto)


def expandir(nome_chave):
    nome_chave = re.sub(r'\b([a-z]{1,4})(\d{1,4})\b', r'\1 \2', nome_chave)
    nome_chave = re.sub(r'\b(\d+)([a-z])\b', r'\1 \2', nome_chave)
    nome_chave = chave(nome_chave)
    palavras = [ABREVIACOES.get(palavra, palavra) for palavra in nome_chave.split()]
    if len(palavras) >= 3 and palavras[0] in TIPOS and palavras[1] in ('n', 'no', 'numero') and palavras[2][0].isdigit():
        del palavras[1]
    return ' '.join(palavras)


@lru_cache(maxsize=1)
def cardinais():
    unidades = 'zero um dois tres quatro cinco seis sete oito nove'.split()
    simples = unidades + 'dez onze doze treze quatorze quinze dezesseis dezessete dezoito dezenove'.split()
    numeros = {nome: valor for valor, nome in enumerate(simples)}
    numeros.update(uma=1, duas=2, catorze=14)
    for dezena, nome in enumerate('vinte trinta quarenta cinquenta sessenta setenta oitenta noventa'.split(), 2):
        numeros[nome] = 10 * dezena
        for unidade in [*unidades[1:], 'uma', 'duas']:
            numeros[f'{nome} e {unidade}'] = 10 * dezena + numeros[unidade]
    menores = list(numeros.items())
    numeros.update(cem=100, mil=1000)
    centenas = 'cento duzentos trezentos quatrocentos quinhentos seiscentos setecentos oitocentos novecentos'
    for centena, nome in enumerate(centenas.split(), 1):
        formas = [nome] if centena == 1 else [nome, nome[:-2] + 'as']
        for forma in formas:
            if centena > 1:
                numeros[forma] = centena * 100
            for resto, valor in menores:
                if valor:
                    numeros[f'{forma} e {resto}'] = centena * 100 + valor
    return numeros


@lru_cache(maxsize=4096)
def numero_por_extenso(nome):
    simples = cardinais().get(nome)
    if simples is not None:
        return simples
    escalas = {'mil': 1000}
    potencias = {'milh': 2, 'bilh': 3, 'trilh': 4, 'quadrilh': 5, 'quatrilh': 5,
                 'quintilh': 6, 'sextilh': 7, 'septilh': 8, 'octilh': 9,
                 'nonilh': 10, 'decilh': 11}
    for radical, potencia in potencias.items():
        for sufixo in ('ao', 'oes'):
            escalas[radical + sufixo] = 1000 ** potencia
    total = 0
    anterior = float('inf')
    grupo = []
    for palavra in nome.split():
        escala = escalas.get(palavra)
        if escala is None:
            grupo.append(palavra)
            continue
        if total and grupo and grupo[0] == 'e':
            grupo = grupo[1:]
        valor = cardinais().get(' '.join(grupo)) if grupo else 1
        if escala >= anterior or valor is None or not 0 < valor < 1000:
            return None
        total += valor * escala
        anterior = escala
        grupo = []
    if not total:
        return None
    if grupo == ['e']:
        return None
    if grupo and grupo[0] == 'e':
        grupo = grupo[1:]
    resto = cardinais().get(' '.join(grupo)) if grupo else 0
    if resto is None or resto >= anterior:
        return None
    return total + resto


@lru_cache(maxsize=4096)
def via_numerada(nome):
    nome = expandir(nome)
    numero = nome if nome.isdigit() else numero_por_extenso(nome)
    if numero is not None:
        return str(numero)
    tipo, _, designacao = nome.partition(' ')
    if tipo not in TIPOS:
        return None
    designacao = re.sub(r'^(?:n|no|numero) ', '', designacao)
    numero = designacao if designacao.isdigit() else numero_por_extenso(designacao)
    if numero is not None:
        return f'{tipo} {numero}'


def variantes_bairro(bairro):
    bairro_chave = chave(bairro)
    if not bairro_chave:
        return []
    prefixo, _, resto = bairro_chave.partition(' ')
    if prefixo == 'st' and resto:
        return [f'setor {resto}']
    if prefixo in PREFIXOS_BAIRRO:
        return [bairro_chave]
    return [bairro_chave, *(f'{prefixo} {bairro_chave}' for prefixo in PREFIXOS_BAIRRO)]


@dataclass(frozen=True)
class Entrada:
    nome: str
    bairro: str | None
    cep: str | None
    cep_geral: bool = False
    conflito: bool = False


def interpretar(termo, bairro):
    localidade = LOCALIDADE.findall(termo)
    if any(chave(uf) not in ('go', 'goias') for uf in localidade):
        return Entrada('', bairro, None, conflito=True)
    texto = LOCALIDADE.sub('', termo)
    ceps = {re.sub(r'\D', '', cep) for cep in CEP_NO_TEXTO.findall(texto)}
    if len(ceps) > 1:
        return Entrada('', bairro, None, conflito=True)
    texto = CEP_NO_TEXTO.sub('', texto)
    partes = [parte.strip() for parte in texto.split(',') if chave(parte)]
    partes = [parte for parte in partes if not COMPLEMENTO.fullmatch(chave(parte))]
    if len(partes) > 1 or (ceps and len(partes) == 1 and texto.lstrip().startswith(',')):
        bairro_informado = partes[-1]
        if bairro and not set(variantes_bairro(bairro)).intersection(variantes_bairro(bairro_informado)):
            return Entrada('', bairro, None, conflito=True)
        bairro = bairro or bairro_informado
        partes.pop()
    nome_informado = ' '.join(partes)
    numero = NUMERO_EXPLICITO.search(nome_informado)
    # Em «Rua nº 19», 19 identifica a própria via, não o imóvel.
    if numero and expandir(chave(nome_informado[:numero.start()])) not in TIPOS:
        nome_informado = NUMERO_EXPLICITO.sub('', nome_informado)
    nome = chave(nome_informado)
    digitos = next(iter(ceps), None)
    cep = f'{digitos[:5]}-{digitos[5:]}' if digitos else None
    cep_geral = bool(cep == '75650-000' and nome)
    return Entrada(nome, bairro, None if cep_geral else cep, cep_geral=cep_geral)


def separar_bairro(nome, bairros):
    opcoes = set()
    for bairro in bairros:
        chave_bairro = chave(bairro)
        if not chave_bairro:
            continue
        opcoes.add(chave_bairro)
        prefixo, _, restante = chave_bairro.partition(' ')
        if prefixo in PREFIXOS_BAIRRO and restante:
            opcoes.add(restante)
    for sufixo in sorted(opcoes, key=lambda bairro: (-len(bairro), bairro)):
        if nome.endswith(f' {sufixo}'):
            restante = nome.removesuffix(f' {sufixo}')
            if any(palavra not in TIPOS for palavra in expandir(restante).split()):
                return restante, sufixo
    return nome, None


def pontuador(nome):
    buscadas = set(expandir(nome).split())

    @lru_cache(maxsize=None)
    def pontuar(candidato):
        if not candidato:
            return 0
        palavras = set(expandir(candidato).split())
        faltam = buscadas - palavras
        if not faltam:
            return 3
        if any(palavra[0].isdigit() or palavra in TIPOS for palavra in faltam):
            return 0
        nao_prefixos = {termo for termo in faltam if len(termo) < 3 or
                        not any(palavra.startswith(termo) for palavra in palavras)}
        if not nao_prefixos:
            return 2
        if len(nao_prefixos) != 1:
            return 0
        termo, = nao_prefixos
        if len(termo) < 5:
            return 0
        candidatos = (palavra for palavra in palavras - buscadas
                     if len(palavra) >= 5 and abs(len(palavra) - len(termo)) <= 2 and palavra[0] == termo[0])
        if any(SequenceMatcher(None, termo, palavra).ratio() >= .82 for palavra in candidatos):
            return 1
        return 0

    return pontuar
