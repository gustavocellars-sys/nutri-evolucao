import os
import base64
import random
import string
import unicodedata

from io import BytesIO
from datetime import date, datetime

import streamlit as st
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)

from google_sheets import (
    listar_pacientes,
    adicionar_paciente,
    listar_pesagens,
    adicionar_pesagem,
    listar_pesagens_por_paciente,
    editar_pesagem,
    excluir_pesagem,
    atualizar_ciclo_paciente,
)


# =========================================================
# IDENTIDADE PROFISSIONAL
# =========================================================

NOME_PROFISSIONAL = "Andrea Cella Nutricionista"
SUBTITULO_APP = "Acompanhamento de evolução corporal"


# =========================================================
# CONFIGURAÇÃO
# =========================================================

st.set_page_config(
    page_title=NOME_PROFISSIONAL,
    page_icon="🥗",
    layout="centered",
)

CONFIG_GRAFICO_PACIENTE = {
    "displayModeBar": False,
    "scrollZoom": False,
    "staticPlot": True
}

# =========================================================
# ESTILO
# =========================================================

st.markdown(
    """
    <style>

    div.stButton > button {
        min-height: 3.2rem;
        font-size: 1.05rem;
        font-weight: 600;
        border-radius: 10px;
        margin-bottom: 0.25rem;
    }

    div[data-baseweb="input"] input {
        min-height: 2.8rem;
        font-size: 1rem;
    }

    .cabecalho-profissional {
        text-align: center;
        margin-bottom: 1.4rem;
    }

    .cabecalho-profissional h1 {
        margin-bottom: 0.2rem;
    }

    .cabecalho-profissional p {
        color: #777;
        font-size: 1.05rem;
        margin-top: 0;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================

def normalizar_nome_para_codigo(nome):

    nome = nome.strip().upper()

    nome_sem_acentos = "".join(
        caractere
        for caractere in unicodedata.normalize("NFD", nome)
        if unicodedata.category(caractere) != "Mn"
    )

    return "".join(
        caractere
        for caractere in nome_sem_acentos
        if caractere.isalpha()
    )


def gerar_codigo_acesso(nome, nascimento, pacientes):

    nome_normalizado = normalizar_nome_para_codigo(nome)

    prefixo = nome_normalizado[:4].ljust(4, "X")

    dia = nascimento.strftime("%d")

    codigo_inicial = f"{prefixo}{dia}"

    codigos_existentes = {
        str(
            paciente.get("codigo_acesso", "")
        ).strip().upper()
        for paciente in pacientes
    }

    if codigo_inicial not in codigos_existentes:
        return codigo_inicial

    while True:

        numero = random.randint(0, 99)

        codigo = f"{prefixo}{numero:02d}"

        if codigo not in codigos_existentes:
            return codigo


def gerar_id_paciente(pacientes):

    numeros = []

    for paciente in pacientes:

        id_atual = str(
            paciente.get("id_paciente", "")
        )

        try:
            numeros.append(
                int(id_atual.replace("P", ""))
            )
        except ValueError:
            pass

    if not numeros:
        return "P0001"

    return f"P{max(numeros) + 1:04d}"


def gerar_id_pesagem(pesagens):

    numeros = []

    for pesagem in pesagens:

        id_atual = str(
            pesagem.get("id_pesagem", "")
        )

        try:
            numeros.append(
                int(id_atual.replace("AV", ""))
            )
        except ValueError:
            pass

    if not numeros:
        return "AV0001"

    return f"AV{max(numeros) + 1:04d}"


def buscar_paciente_por_codigo(codigo, pacientes):

    codigo = codigo.strip().upper()

    for paciente in pacientes:

        if str(
            paciente.get("codigo_acesso", "")
        ).strip().upper() == codigo:

            return paciente

    return None


def buscar_paciente_por_id(id_paciente, pacientes):

    for paciente in pacientes:

        if str(
            paciente.get("id_paciente", "")
        ).strip() == str(id_paciente).strip():

            return paciente

    return None


def converter_numero(valor):

    if valor is None:
        return 0.0

    texto = str(valor).strip()

    if texto == "":
        return 0.0

    texto = texto.replace(",", ".")

    try:
        return float(texto)

    except ValueError:
        return 0.0


def converter_inteiro(valor):

    try:
        return int(float(str(valor).replace(",", ".")))

    except (ValueError, TypeError):
        return 0


def converter_data(valor):

    try:
        return datetime.strptime(
            str(valor),
            "%d/%m/%Y"
        )

    except ValueError:
        return datetime.min


def converter_data_para_date(valor):

    try:
        return datetime.strptime(
            str(valor),
            "%d/%m/%Y"
        ).date()

    except ValueError:
        return date.today()


def formatar_numero(numero, casas=1):

    return f"{numero:.{casas}f}".replace(".", ",")


def formatar_percentual_regional(valor):
    """
    Formata um percentual regional da BF1000.
    Registros antigos sem esse dado aparecem como traço.
    """

    if valor is None:
        return "—"

    texto = str(valor).strip()

    if texto == "":
        return "—"

    try:
        numero = float(
            texto.replace(",", ".")
        )
    except (ValueError, TypeError):
        return "—"

    return f"{formatar_numero(numero)}%"


def renderizar_distribuicao_gordura(ultima):
    """
    Mostra a distribuição regional de gordura da última avaliação
    sobre a imagem boneco_corpo.png.

    O boneco é visto de frente:
    - o lado direito anatômico fica à esquerda de quem observa;
    - o lado esquerdo anatômico fica à direita de quem observa.
    """

    caminho_boneco = "boneco_corpo.png"

    if not os.path.exists(caminho_boneco):
        st.info(
            "A distribuição regional estará disponível "
            "quando a imagem infográfica for adicionada."
        )
        return

    with open(caminho_boneco, "rb") as arquivo:
        imagem_b64 = base64.b64encode(
            arquivo.read()
        ).decode("utf-8")

    braco_direito = formatar_percentual_regional(
        ultima.get(
            "gordura_braco_direito_pct",
            ""
        )
    )

    braco_esquerdo = formatar_percentual_regional(
        ultima.get(
            "gordura_braco_esquerdo_pct",
            ""
        )
    )

    perna_direita = formatar_percentual_regional(
        ultima.get(
            "gordura_perna_direita_pct",
            ""
        )
    )

    perna_esquerda = formatar_percentual_regional(
        ultima.get(
            "gordura_perna_esquerda_pct",
            ""
        )
    )
    gordura_abdominal = formatar_percentual_regional(
        ultima.get(
            "gordura_abdominal",
            ""
        )
    )
    st.html(
        f"""
<div style="
    position:relative;
    width:100%;
    max-width:390px;
    aspect-ratio:2 / 3;
    margin:0 auto 10px auto;
">

    <img
        src="data:image/png;base64,{imagem_b64}"
        style="
            position:absolute;
            inset:0;
            width:100%;
            height:100%;
            object-fit:contain;
        "
    />

    <!-- Braço direito anatômico: lado esquerdo de quem olha -->
    <div style="
        position:absolute;
        top:36%;
        left:31%;
        transform:translate(-50%, -50%);
        min-width:52px;
        text-align:center;
        padding:4px 6px;
        border-radius:10px;
        background:rgba(255,255,255,0.82);
        font-size:15px;
        font-weight:700;
        box-shadow:0 1px 5px rgba(0,0,0,0.10);
    ">
        {braco_direito}
    </div>

    <!-- Braço esquerdo anatômico: lado direito de quem olha -->
    <div style="
        position:absolute;
        top:36%;
        left:69%;
        transform:translate(-50%, -50%);
        min-width:52px;
        text-align:center;
        padding:4px 6px;
        border-radius:10px;
        background:rgba(255,255,255,0.82);
        font-size:15px;
        font-weight:700;
        box-shadow:0 1px 5px rgba(0,0,0,0.10);
    ">
        {braco_esquerdo}
    </div>

    <!-- Perna direita anatômica -->
    <div style="
        position:absolute;
        top:66%;
        left:42%;
        transform:translate(-50%, -50%);
        min-width:52px;
        text-align:center;
        padding:4px 6px;
        border-radius:10px;
        background:rgba(255,255,255,0.82);
        font-size:15px;
        font-weight:700;
        box-shadow:0 1px 5px rgba(0,0,0,0.10);
    ">
        {perna_direita}
    </div>

    <!-- Perna esquerda anatômica -->
    <div style="
        position:absolute;
        top:66%;
        left:58%;
        transform:translate(-50%, -50%);
        min-width:52px;
        text-align:center;
        padding:4px 6px;
        border-radius:10px;
        background:rgba(255,255,255,0.82);
        font-size:15px;
        font-weight:700;
        box-shadow:0 1px 5px rgba(0,0,0,0.10);
    ">
        {perna_esquerda}
    </div>
    <!-- Gordura abdominal -->
    <div style="
        position:absolute;
        top:46%;
        left:50%;
        transform:translate(-50%, -50%);
        min-width:52px;
        text-align:center;
        padding:4px 6px;
        border-radius:10px;
        background:rgba(255,255,255,0.82);
        font-size:15px;
        font-weight:700;
        box-shadow:0 1px 5px rgba(0,0,0,0.10);
    ">
        {gordura_abdominal}
    </div>
</div>
"""
    )


# =========================================================
# FAIXAS DE REFERÊNCIA DOS GRÁFICOS
# =========================================================

def calcular_idade(nascimento):
    """
    Calcula a idade atual a partir do campo nascimento.

    Aceita os formatos mais comuns que podem chegar do
    Google Sheets/Streamlit:
    DD/MM/AAAA, AAAA-MM-DD, DD-MM-AAAA e AAAA/MM/DD.
    """

    if nascimento is None:
        return None

    if isinstance(nascimento, datetime):
        data_nascimento = nascimento.date()

    elif isinstance(nascimento, date):
        data_nascimento = nascimento

    else:
        texto = str(nascimento).strip()

        if not texto:
            return None

        # Remove horário caso o Google Sheets retorne algo
        # como "1985-04-07 00:00:00".
        texto_sem_hora = texto.split(" ")[0]

        formatos = [
            "%d/%m/%Y",
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%Y/%m/%d",
        ]

        data_nascimento = None

        for formato in formatos:
            try:
                data_nascimento = datetime.strptime(
                    texto_sem_hora,
                    formato
                ).date()
                break
            except ValueError:
                continue

        if data_nascimento is None:
            return None

    hoje = date.today()

    if data_nascimento > hoje:
        return None

    return (
        hoje.year
        - data_nascimento.year
        - (
            (hoje.month, hoje.day)
            < (data_nascimento.month, data_nascimento.day)
        )
    )


def obter_faixas_referencia(paciente):
    """
    Retorna as faixas de referência usadas nos gráficos.

    IMC:
        Adultos (>= 18 anos): 18,5 a 24,9 kg/m².

    Gordura visceral:
        BF1000: 1 a 12.

    Água corporal:
        BF1000:
        - Masculino: 50 a 65 %
        - Feminino: 45 a 60 %

    Gordura corporal e músculo:
        Faixa 'Normal' da BF1000 conforme sexo e idade.
    """

    idade = calcular_idade(
        paciente.get("nascimento", "")
    )

    sexo = str(
        paciente.get("sexo", "")
    ).strip().lower()

    referencias = {
        "imc": None,
        "gordura_visceral": (1, 12),
        "agua": None,
        "gordura": None,
        "musculo": None,
    }

    # IMC: faixa de referência para adultos.
    if idade is not None and idade >= 18:
        referencias["imc"] = (18.5, 24.9)

    # Água corporal BF1000.
    if sexo == "masculino":
        referencias["agua"] = (50, 65)
    elif sexo == "feminino":
        referencias["agua"] = (45, 60)

    # Gordura corporal BF1000 — faixa "Normal".
    gordura_masculino = [
        (10, 14, 11, 16),
        (15, 19, 12, 17),
        (20, 29, 13, 18),
        (30, 39, 14, 19),
        (40, 49, 15, 20),
        (50, 59, 16, 21),
        (60, 69, 17, 22),
        (70, 100, 18, 23),
    ]

    gordura_feminino = [
        (10, 14, 16, 21),
        (15, 19, 17, 22),
        (20, 29, 18, 23),
        (30, 39, 19, 24),
        (40, 49, 20, 25),
        (50, 59, 21, 26),
        (60, 69, 22, 27),
        (70, 100, 23, 28),
    ]

    # Percentual muscular BF1000 — faixa "Normal".
    musculo_masculino = [
        (10, 14, 44, 57),
        (15, 19, 43, 56),
        (20, 29, 42, 54),
        (30, 39, 41, 52),
        (40, 49, 40, 50),
        (50, 59, 39, 48),
        (60, 69, 38, 47),
        (70, 100, 37, 46),
    ]

    musculo_feminino = [
        (10, 14, 36, 43),
        (15, 19, 35, 41),
        (20, 29, 34, 39),
        (30, 39, 33, 38),
        (40, 49, 31, 36),
        (50, 59, 29, 34),
        (60, 69, 28, 33),
        (70, 100, 27, 32),
    ]

    if idade is None:
        return referencias

    if sexo == "masculino":
        tabela_gordura = gordura_masculino
        tabela_musculo = musculo_masculino
    elif sexo == "feminino":
        tabela_gordura = gordura_feminino
        tabela_musculo = musculo_feminino
    else:
        return referencias

    for idade_min, idade_max, minimo, maximo in tabela_gordura:
        if idade_min <= idade <= idade_max:
            referencias["gordura"] = (minimo, maximo)
            break

    for idade_min, idade_max, minimo, maximo in tabela_musculo:
        if idade_min <= idade <= idade_max:
            referencias["musculo"] = (minimo, maximo)
            break

    return referencias


def formatar_eixo_data(figura):
    """
    Exibe somente a data nos gráficos, sem hora/minuto/segundo.
    """

    figura.update_xaxes(
        tickformat="%d/%m/%Y",
        hoverformat="%d/%m/%Y"
    )

    return figura


def adicionar_faixa_referencia(figura, limite_minimo, limite_maximo):
    """
    Adiciona uma área horizontal discreta ao gráfico Plotly,
    identificada como 'Faixa de referência', e garante que
    tanto a faixa quanto os dados do paciente fiquem visíveis.
    """

    if limite_minimo is None or limite_maximo is None:
        return figura

    figura.add_hrect(
        y0=limite_minimo,
        y1=limite_maximo,
        fillcolor="#8FBFA8",
        opacity=0.16,
        line_width=0,
        annotation_text="Faixa de referência",
        annotation_position="top left"
    )

    figura.add_hline(
        y=limite_minimo,
        line_dash="dot",
        line_width=1,
        line_color="#6F8F7C"
    )

    figura.add_hline(
        y=limite_maximo,
        line_dash="dot",
        line_width=1,
        line_color="#6F8F7C"
    )

    # Garante que a escala automática não esconda a faixa
    # quando os resultados do paciente estiverem distantes dela.
    valores = [
        float(limite_minimo),
        float(limite_maximo),
    ]

    for trace in figura.data:
        valores_trace = getattr(trace, "y", None)

        if valores_trace is None:
            continue

        for valor in valores_trace:
            try:
                numero = float(valor)

                # Ignora NaN/inf.
                if numero == numero and abs(numero) != float("inf"):
                    valores.append(numero)

            except (ValueError, TypeError):
                continue

    if valores:
        menor = min(valores)
        maior = max(valores)

        amplitude = maior - menor

        if amplitude <= 0:
            amplitude = max(abs(maior), 1.0)

        margem = max(amplitude * 0.12, 0.5)

        figura.update_yaxes(
            range=[
                menor - margem,
                maior + margem
            ]
        )

    return figura

# =========================================================
# CICLO MENSTRUAL
# =========================================================

def calcular_fase_do_ciclo(
    ultima_menstruacao,
    ciclo_medio_dias,
    data_atual=None
):

    if data_atual is None:
        data_atual = date.today()

    if isinstance(
        ultima_menstruacao,
        str
    ):

        try:

            ultima_menstruacao = (
                datetime.strptime(
                    ultima_menstruacao,
                    "%d/%m/%Y"
                ).date()
            )

        except ValueError:
            return None


    try:

        ciclo = int(
            ciclo_medio_dias
        )

    except (
        ValueError,
        TypeError
    ):

        return None


    if ciclo < 14 or ciclo > 50:
        return None


    # Não calcula para datas futuras
    if ultima_menstruacao > data_atual:
        return None


    # Quantos dias se passaram
    dias_passados = (
        data_atual
        - ultima_menstruacao
    ).days


    # Dia atual do ciclo.
    # O primeiro dia da menstruação é Dia 1.
    dia_do_ciclo = (
        dias_passados % ciclo
    ) + 1


    # Ovulação estimada:
    # aproximadamente 14 dias antes
    # da próxima menstruação.
    ovulacao_estimada = max(
        1,
        ciclo - 14
    )


    # ---------------------------------------------
    # LIMITES DAS FASES
    # ---------------------------------------------

    fim_menstrual = min(
        5,
        ciclo
    )


    # Janela ovulatória:
    # aproximadamente 2 dias antes
    # até 1 dia depois da ovulação.
    #
    # Evitamos sobreposição com
    # os cinco primeiros dias menstruais.
    inicio_ovulatoria = max(
        fim_menstrual + 1,
        ovulacao_estimada - 2
    )

    fim_ovulatoria = min(
        ciclo,
        max(
            inicio_ovulatoria,
            ovulacao_estimada + 1
        )
    )


    # ---------------------------------------------
    # CLASSIFICAÇÃO
    # ---------------------------------------------

    if dia_do_ciclo <= fim_menstrual:

        numero_fase = 1

        nome_fase = (
            "A Sábia Anciã"
        )

        fase_biologica = (
            "Fase menstrual"
        )

        imagem = "ancia.png"

        descricao = (
            "Um período de maior recolhimento, "
            "percepção interna e renovação."
        )


    elif (
        dia_do_ciclo
        < inicio_ovulatoria
    ):

        numero_fase = 2

        nome_fase = (
            "A Jovem Exploradora"
        )

        fase_biologica = (
            "Fase folicular"
        )

        imagem = "jovem.png"

        descricao = (
            "Um período associado à renovação, "
            "curiosidade, crescimento e movimento."
        )


    elif (
        inicio_ovulatoria
        <= dia_do_ciclo
        <= fim_ovulatoria
    ):

        numero_fase = 3

        nome_fase = (
            "A Mãe Amorosa"
        )

        fase_biologica = (
            "Fase ovulatória"
        )

        imagem = "mae.png"

        descricao = (
            "Um período associado à conexão, "
            "acolhimento, comunicação e expansão."
        )


    else:

        numero_fase = 4

        nome_fase = (
            "A Feiticeira"
        )

        fase_biologica = (
            "Fase lútea"
        )

        imagem = "feiticeira.png"

        descricao = (
            "Um período associado à introspecção, "
            "intuição, transformação e preparação "
            "para um novo ciclo."
        )


    # Quantos dias até o próximo
    # Dia 1 estimado
    dias_para_proxima = (
        ciclo
        - dia_do_ciclo
        + 1
    )


    return {

        "dia_do_ciclo":
            dia_do_ciclo,

        "numero_fase":
            numero_fase,

        "nome_fase":
            nome_fase,

        "fase_biologica":
            fase_biologica,

        "imagem":
            imagem,

        "descricao":
            descricao,

        "dias_para_proxima_menstruacao":
            dias_para_proxima,

        "ovulacao_estimada":
            ovulacao_estimada,

        "inicio_ovulatoria":
            inicio_ovulatoria,

        "fim_ovulatoria":
            fim_ovulatoria,
    }
def paciente_e_feminina(paciente):

    sexo = str(
        paciente.get(
            "sexo",
            ""
        )
    ).strip().lower()

    return sexo == "feminino"

# =========================================================
# PDF
# =========================================================

def criar_grafico_pdf(
    pesagens,
    campo,
    titulo,
    unidade
):

    datas = [
        pesagem["data"]
        for pesagem in pesagens
    ]

    valores = [
        converter_numero(
            pesagem.get(campo, 0)
        )
        for pesagem in pesagens
    ]

    fig, ax = plt.subplots(
        figsize=(7, 3)
    )

    ax.plot(
        datas,
        valores,
        marker="o"
    )

    ax.set_title(titulo)

    ax.set_ylabel(unidade)

    ax.grid(
        True,
        alpha=0.25
    )

    plt.xticks(
        rotation=30,
        ha="right"
    )

    plt.tight_layout()

    imagem = BytesIO()

    fig.savefig(
        imagem,
        format="png",
        dpi=150,
        bbox_inches="tight"
    )

    plt.close(fig)

    imagem.seek(0)

    return imagem


def gerar_pdf_paciente(
    paciente,
    pesagens
):

    buffer = BytesIO()

    documento = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    estilos = getSampleStyleSheet()

    elementos = []

    if os.path.exists("logo.png"):

        elementos.append(
            Image(
                "logo.png",
                width=5 * cm,
                height=2.5 * cm
            )
        )

        elementos.append(
            Spacer(1, 0.4 * cm)
        )

    elementos.append(
        Paragraph(
            NOME_PROFISSIONAL,
            estilos["Title"]
        )
    )

    elementos.append(
        Paragraph(
            "Relatório de evolução corporal",
            estilos["Heading2"]
        )
    )

    elementos.append(
        Spacer(1, 0.5 * cm)
    )

    elementos.append(
        Paragraph(
            f"<b>Paciente:</b> {paciente['nome']}",
            estilos["Normal"]
        )
    )

    elementos.append(
        Paragraph(
            f"<b>Data do relatório:</b> "
            f"{date.today().strftime('%d/%m/%Y')}",
            estilos["Normal"]
        )
    )

    elementos.append(
        Spacer(1, 0.7 * cm)
    )

    ultima = pesagens[-1]

    elementos.append(
        Paragraph(
            "Última avaliação",
            estilos["Heading2"]
        )
    )

    dados_ultima = [
        ["Indicador", "Resultado"],
        ["Data", ultima["data"]],
        ["Peso", f"{ultima['peso_kg']} kg"],
        ["IMC", ultima["imc"]],
        ["Gordura corporal", f"{ultima['gordura_pct']} %"],
        ["Água corporal", f"{ultima['agua_pct']} %"],
        ["Músculo", f"{ultima['musculo_pct']} %"],
        ["Massa óssea", f"{ultima['massa_ossea_kg']} kg"],
        ["Gordura visceral", ultima["gordura_visceral"]],
        ["Gordura abdominal", ultima["gordura_abdominal"]],
        ["Cintura", f"{ultima['cintura_cm']} cm"],
        ["Abdômen", f"{ultima['abdomen_cm']} cm"],
        ["Quadril", f"{ultima['quadril_cm']} cm"],
        ["Braço", f"{ultima['braco_cm']} cm"],
        ["Coxa", f"{ultima['coxa_cm']} cm"],
    ]

    tabela = Table(
        dados_ultima,
        colWidths=[
            8 * cm,
            8 * cm
        ]
    )

    tabela.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#E8F2ED")
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold"
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.3,
                    colors.lightgrey
                ),
                (
                    "PADDING",
                    (0, 0),
                    (-1, -1),
                    7
                ),
            ]
        )
    )

    elementos.append(tabela)

    elementos.append(
        Spacer(1, 0.8 * cm)
    )

    graficos = [
        (
            "peso_kg",
            "Evolução do peso",
            "kg"
        ),
        (
            "gordura_pct",
            "Evolução da gordura corporal",
            "%"
        ),
        (
            "musculo_pct",
            "Evolução muscular",
            "%"
        ),
    ]

    for campo, titulo, unidade in graficos:

        imagem = criar_grafico_pdf(
            pesagens,
            campo,
            titulo,
            unidade
        )

        elementos.append(
            Paragraph(
                titulo,
                estilos["Heading2"]
            )
        )

        elementos.append(
            Image(
                imagem,
                width=17 * cm,
                height=7 * cm
            )
        )

        elementos.append(
            Spacer(1, 0.5 * cm)
        )

    elementos.append(
        Paragraph(
            "Histórico de avaliações",
            estilos["Heading2"]
        )
    )

    dados_historico = [
        [
            "Data",
            "Peso",
            "IMC",
            "Gordura",
            "Músculo"
        ]
    ]

    for pesagem in reversed(pesagens):

        dados_historico.append(
            [
                pesagem["data"],
                pesagem["peso_kg"],
                pesagem["imc"],
                pesagem["gordura_pct"],
                pesagem["musculo_pct"],
            ]
        )

    tabela_historico = Table(
        dados_historico,
        repeatRows=1
    )

    tabela_historico.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#E8F2ED")
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold"
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.3,
                    colors.lightgrey
                ),
                (
                    "ALIGN",
                    (1, 1),
                    (-1, -1),
                    "CENTER"
                ),
                (
                    "PADDING",
                    (0, 0),
                    (-1, -1),
                    5
                ),
            ]
        )
    )

    elementos.append(
        tabela_historico
    )

    documento.build(
        elementos
    )

    buffer.seek(0)

    return buffer.getvalue()


# =========================================================
# CARREGAMENTO
# =========================================================

try:

    pacientes = listar_pacientes()

except Exception as erro:

    st.error(
        "Não foi possível acessar o Google Sheets."
    )

    st.exception(erro)

    st.stop()


# =========================================================
# CABEÇALHO
# =========================================================

if os.path.exists("logo.png"):

    _, coluna_logo, _ = st.columns(
        [1, 2, 1]
    )

    with coluna_logo:

        st.image(
            "logo.png",
            use_container_width=True
        )

    st.markdown(
        f"""
        <div class="cabecalho-profissional">
            <p>{SUBTITULO_APP}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

else:

    st.markdown(
        f"""
        <div class="cabecalho-profissional">
            <h1>{NOME_PROFISSIONAL}</h1>
            <p>{SUBTITULO_APP}</p>
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# TELA INICIAL
# =========================================================

if not st.session_state.get("area"):

    st.write(
        "Acesse seus resultados de avaliações corporais."
    )

    if st.button(
        "👤 ACESSAR COMO PACIENTE",
        type="primary",
        use_container_width=True
    ):

        st.session_state["area"] = "paciente"

        st.rerun()

    st.caption(
        "Utilize o código de identificação "
        "fornecido pela nutricionista."
    )

    st.write("")
    st.divider()

    _, col_profissional = st.columns(
        [2, 1]
    )

    with col_profissional:

        if st.button(
            "🩺 Área profissional",
            use_container_width=True
        ):

            st.session_state[
                "area"
            ] = "profissional"

            st.rerun()


# =========================================================
# ÁREA PACIENTE
# =========================================================

elif st.session_state.get("area") == "paciente":

    st.subheader(
        "👤 Área do Paciente"
    )

    if "paciente_logado_id" not in st.session_state:

        codigo = st.text_input(
            "Código de identificação",
            placeholder="Ex.: JOAO07"
        )

        if st.button(
            "Acessar meus resultados",
            type="primary",
            use_container_width=True
        ):

            paciente = (
                buscar_paciente_por_codigo(
                    codigo,
                    pacientes
                )
                if codigo
                else None
            )

            if paciente:

                st.session_state[
                    "paciente_logado_id"
                ] = paciente[
                    "id_paciente"
                ]

                st.rerun()

            else:

                st.error(
                    "Código não encontrado."
                )

        if st.button("← Voltar"):

            st.session_state["area"] = None

            st.rerun()

    else:

        paciente = buscar_paciente_por_id(
            st.session_state[
                "paciente_logado_id"
            ],
            pacientes
        )

        if paciente is None:

            st.error(
                "Paciente não encontrado."
            )

            del st.session_state[
                "paciente_logado_id"
            ]

            st.stop()

        col_nome, col_sair = st.columns(
            [4, 1]
        )

        with col_nome:

            st.write(
                f"### Olá, {paciente['nome']} 👋"
            )

        with col_sair:

            if st.button(
                "Sair",
                key="sair_paciente",
                use_container_width=True
            ):

                del st.session_state[
                    "paciente_logado_id"
                ]

                st.session_state[
                    "area"
                ] = None

                st.rerun()
        # =====================================================
        # CICLO MENSTRUAL / MENOPAUSA
        # =====================================================

        if paciente_e_feminina(
            paciente
        ):

            ultima_menstruacao_salva = str(
                paciente.get(
                    "ultima_menstruacao",
                    ""
                )
            ).strip()

            ciclo_salvo = str(
                paciente.get(
                    "ciclo_medio_dias",
                    ""
                )
            ).strip()

            menopausa_salva = str(
                paciente.get(
                    "menopausa",
                    ""
                )
            ).strip().upper()

            esta_na_menopausa = (
                menopausa_salva == "SIM"
            )

            possui_dados_ciclo = (
                ultima_menstruacao_salva != ""
                and ciclo_salvo != ""
            )

            st.divider()

            if esta_na_menopausa:

                if os.path.exists("ancia.png"):

                    col_img1, col_img2, col_img3 = st.columns(
                        [1.3, 1, 1.3]
                    )

                    with col_img2:
                        st.image(
                            "ancia.png",
                            use_container_width=True
                        )

                st.markdown(
                    """
<div style="
    text-align:center;
    padding:24px;
    border-radius:16px;
    background-color:#F4F7F5;
    margin-bottom:15px;
">

<div style="
    font-size:25px;
    font-weight:700;
">
A Sábia Anciã
</div>

<div style="
    font-size:16px;
    margin-top:6px;
    color:#666;
">
Menopausa
</div>

<div style="
    font-size:15px;
    margin-top:16px;
">
Uma fase de sabedoria, introspecção, autoconhecimento
e novos ciclos de vida.
</div>

</div>
""",
                    unsafe_allow_html=True
                )

                if st.button(
                    "⚙️ Alterar situação",
                    use_container_width=True,
                    key="botao_alterar_situacao_menopausa"
                ):

                    st.session_state[
                        "editando_ciclo"
                    ] = True

            elif possui_dados_ciclo:

                resultado_ciclo = calcular_fase_do_ciclo(
                    ultima_menstruacao_salva,
                    ciclo_salvo
                )

                if resultado_ciclo:

                    imagem_fase = resultado_ciclo["imagem"]

                    if os.path.exists(imagem_fase):

                        col_img1, col_img2, col_img3 = st.columns(
                            [1.3, 1, 1.3]
                        )

                        with col_img2:
                            st.image(
                                imagem_fase,
                                use_container_width=True
                            )

                    st.markdown(
                        f"""
<div style="
    text-align:center;
    padding:24px;
    border-radius:16px;
    background-color:#F4F7F5;
    margin-bottom:15px;
">

<div style="
    font-size:15px;
    color:#666;
">
Hoje você está no
</div>

<div style="
    font-size:22px;
    font-weight:700;
    margin-top:4px;
">
Dia {resultado_ciclo['dia_do_ciclo']} do seu ciclo
</div>

<div style="
    font-size:25px;
    font-weight:700;
    margin-top:18px;
">
Fase {resultado_ciclo['numero_fase']} — {resultado_ciclo['nome_fase']}
</div>

<div style="
    font-size:16px;
    margin-top:5px;
    color:#666;
">
{resultado_ciclo['fase_biologica']}
</div>

<div style="
    font-size:15px;
    margin-top:16px;
">
{resultado_ciclo['descricao']}
</div>

<div style="
    margin-top:20px;
    font-weight:600;
">
Próxima menstruação estimada em
{resultado_ciclo['dias_para_proxima_menstruacao']} dia(s)
</div>

</div>
""",
                        unsafe_allow_html=True
                    )

                    st.caption(
                        "As fases e datas apresentadas são "
                        "estimativas baseadas na duração média "
                        "informada do ciclo. Não devem ser usadas "
                        "para determinar ovulação, fertilidade "
                        "ou como método contraceptivo."
                    )

                if st.button(
                    "⚙️ Atualizar meu ciclo",
                    use_container_width=True,
                    key="botao_atualizar_ciclo"
                ):

                    st.session_state[
                        "editando_ciclo"
                    ] = True

            else:

                st.info(
                    "🌙 Você pode acompanhar as fases "
                    "do seu ciclo menstrual neste portal."
                )

                if st.button(
                    "🌙 Configurar meu ciclo",
                    use_container_width=True,
                    key="botao_configurar_ciclo"
                ):

                    st.session_state[
                        "editando_ciclo"
                    ] = True

            if st.session_state.get(
                "editando_ciclo",
                False
            ):

                st.write(
                    "### 🌙 Situação menstrual"
                )

                marcar_menopausa = st.checkbox(
                    "Estou na menopausa",
                    value=esta_na_menopausa,
                    key="checkbox_menopausa_paciente"
                )

                if marcar_menopausa:

                    st.caption(
                        "Ao salvar, o acompanhamento de ciclo "
                        "será substituído pela fase A Sábia Anciã. "
                        "Você poderá alterar esta opção depois."
                    )

                    nova_ultima_menstruacao = None
                    novo_ciclo_medio = None

                else:

                    try:
                        data_padrao_ciclo = datetime.strptime(
                            ultima_menstruacao_salva,
                            "%d/%m/%Y"
                        ).date()
                    except ValueError:
                        data_padrao_ciclo = date.today()

                    try:
                        ciclo_padrao = int(
                            ciclo_salvo
                        )

                        if ciclo_padrao < 14 or ciclo_padrao > 50:
                            ciclo_padrao = 28

                    except (
                        ValueError,
                        TypeError
                    ):
                        ciclo_padrao = 28

                    nova_ultima_menstruacao = st.date_input(
                        "Data da última menstruação",
                        value=data_padrao_ciclo,
                        min_value=date(1900, 1, 1),
                        max_value=date.today(),
                        format="DD/MM/YYYY",
                        key="nova_ultima_menstruacao"
                    )

                    novo_ciclo_medio = st.number_input(
                        "Duração média do ciclo (dias)",
                        min_value=14,
                        max_value=50,
                        value=ciclo_padrao,
                        step=1,
                        key="novo_ciclo_medio"
                    )

                    st.caption(
                        "Informe quantos dias, em média, "
                        "há entre o primeiro dia de uma "
                        "menstruação e o primeiro dia da próxima."
                    )

                col_salvar, col_cancelar = st.columns(2)

                with col_salvar:

                    if st.button(
                        "💾 Salvar",
                        type="primary",
                        use_container_width=True,
                        key="salvar_situacao_menstrual"
                    ):

                        if marcar_menopausa:

                            ultima_para_salvar = ""
                            ciclo_para_salvar = ""
                            menopausa_para_salvar = "SIM"

                        else:

                            ultima_para_salvar = (
                                nova_ultima_menstruacao.strftime(
                                    "%d/%m/%Y"
                                )
                            )

                            ciclo_para_salvar = int(
                                novo_ciclo_medio
                            )

                            menopausa_para_salvar = "NAO"

                        sucesso = atualizar_ciclo_paciente(
                            paciente["id_paciente"],
                            ultima_para_salvar,
                            ciclo_para_salvar,
                            menopausa_para_salvar
                        )

                        if sucesso:

                            st.session_state[
                                "editando_ciclo"
                            ] = False

                            st.success(
                                "Situação menstrual atualizada."
                            )

                            st.rerun()

                        else:

                            st.error(
                                "Não foi possível atualizar os dados."
                            )

                with col_cancelar:

                    if st.button(
                        "Cancelar",
                        use_container_width=True,
                        key="cancelar_ciclo"
                    ):

                        st.session_state[
                            "editando_ciclo"
                        ] = False

                        st.rerun()

        try:

            pesagens_paciente = (
                listar_pesagens_por_paciente(
                    paciente["id_paciente"]
                )
            )

            if not pesagens_paciente:

                st.info(
                    "Ainda não existem avaliações cadastradas."
                )

            else:

                pesagens_paciente = sorted(
                    pesagens_paciente,
                    key=lambda x: converter_data(
                        x.get("data", "")
                    )
                )

                pdf = gerar_pdf_paciente(
                    paciente,
                    pesagens_paciente
                )

                st.download_button(
                    "📄 Baixar relatório em PDF",
                    pdf,
                    file_name=(
                        "evolucao_"
                        + paciente["nome"].replace(
                            " ",
                            "_"
                        )
                        + ".pdf"
                    ),
                    mime="application/pdf",
                    use_container_width=True
                )

                primeira = pesagens_paciente[0]

                ultima = pesagens_paciente[-1]

                peso_inicial = converter_numero(
                    primeira["peso_kg"]
                )

                peso_atual = converter_numero(
                    ultima["peso_kg"]
                )

                gordura_inicial = converter_numero(
                    primeira["gordura_pct"]
                )

                gordura_atual = converter_numero(
                    ultima["gordura_pct"]
                )

                musculo_inicial = converter_numero(
                    primeira["musculo_pct"]
                )

                musculo_atual = converter_numero(
                    ultima["musculo_pct"]
                )

                st.divider()

                st.write(
                    "## Última avaliação"
                )

                st.caption(
                    f"Realizada em {ultima['data']}"
                )

                col1, col2 = st.columns(2)

                with col1:

                    st.metric(
                        "⚖️ Peso",
                        f"{formatar_numero(peso_atual)} kg",
                        f"{formatar_numero(
                            peso_atual - peso_inicial
                        )} kg",
                        delta_color="off"
                    )

                    st.metric(
                        "🔥 Gordura corporal",
                        f"{formatar_numero(gordura_atual)} %",
                        f"{formatar_numero(
                            gordura_atual - gordura_inicial
                        )} p.p.",
                        delta_color="off"
                    )

                with col2:

                    st.metric(
                        "📐 IMC",
                        formatar_numero(
                            converter_numero(
                                ultima["imc"]
                            )
                        )
                    )

                    st.metric(
                        "💪 Músculo",
                        f"{formatar_numero(musculo_atual)} %",
                        f"{formatar_numero(
                            musculo_atual - musculo_inicial
                        )} p.p.",
                        delta_color="off"
                    )

                observacao_ultima = str(
                    ultima.get(
                        "observacoes",
                        ""
                    )
                ).strip()

                if observacao_ultima:

                    st.markdown(
                        "### 💬 Comentário da nutricionista"
                    )

                    st.info(
                        observacao_ultima
                    )

                st.markdown(
                    "### Distribuição da gordura pelo corpo"
                )

                renderizar_distribuicao_gordura(
                    ultima
                )

                # =====================================================
                # REFERÊNCIAS DO PACIENTE
                # =====================================================

                referencias = obter_faixas_referencia(
                    paciente
                )


                # =====================================================
                # PREPARAR DADOS DOS GRÁFICOS
                # =====================================================

                dados_grafico = []

                for pesagem in pesagens_paciente:

                    dados_grafico.append(
                        {
                            "Data": converter_data(
                                pesagem["data"]
                            ),
                            "Peso": converter_numero(
                                pesagem["peso_kg"]
                            ),
                            "IMC": converter_numero(
                                pesagem["imc"]
                            ),
                            "Gordura": converter_numero(
                                pesagem["gordura_pct"]
                            ),
                            "Água": converter_numero(
                                pesagem["agua_pct"]
                            ),
                            "Músculo": converter_numero(
                                pesagem["musculo_pct"]
                            ),
                            "Gordura visceral": converter_numero(
                                pesagem["gordura_visceral"]
                            ),
                        }
                    )

                df = pd.DataFrame(
                    dados_grafico
                )


                # =====================================================
                # EVOLUÇÃO DO PESO
                # =====================================================

                st.divider()

                st.write(
                    "## ⚖️ Evolução do peso"
                )

                fig_peso = px.line(
                    df,
                    x="Data",
                    y="Peso",
                    markers=True,
                    labels={
                        "Data": "Data",
                        "Peso": "Peso (kg)"
                    }
                )

                fig_peso.update_layout(
                    xaxis_title="",
                    yaxis_title="Peso (kg)"
                )

                fig_peso = formatar_eixo_data(
                    fig_peso
                )

                st.plotly_chart(
                    fig_peso,
                    use_container_width=True,
                    config=CONFIG_GRAFICO_PACIENTE
                )


                # =====================================================
                # EVOLUÇÃO DO IMC
                # =====================================================

                st.write(
                    "## 📐 Evolução do IMC"
                )

                fig_imc = px.line(
                    df,
                    x="Data",
                    y="IMC",
                    markers=True,
                    labels={
                        "Data": "Data",
                        "IMC": "IMC"
                    }
                )

                fig_imc.update_layout(
                    xaxis_title="",
                    yaxis_title="IMC"
                )

                if referencias["imc"]:

                    fig_imc = adicionar_faixa_referencia(
                        fig_imc,
                        referencias["imc"][0],
                        referencias["imc"][1]
                    )

                fig_imc = formatar_eixo_data(
                    fig_imc
                )

                st.plotly_chart(
                    fig_imc,
                    use_container_width=True,
                    config=CONFIG_GRAFICO_PACIENTE
                )


                # =====================================================
                # EVOLUÇÃO DA GORDURA CORPORAL
                # =====================================================

                st.write(
                    "## 🔥 Evolução da gordura corporal"
                )

                fig_gordura = px.line(
                    df,
                    x="Data",
                    y="Gordura",
                    markers=True,
                    labels={
                        "Data": "Data",
                        "Gordura": "Gordura corporal (%)"
                    }
                )

                fig_gordura.update_layout(
                    xaxis_title="",
                    yaxis_title="Gordura corporal (%)"
                )

                if referencias["gordura"]:

                    fig_gordura = adicionar_faixa_referencia(
                        fig_gordura,
                        referencias["gordura"][0],
                        referencias["gordura"][1]
                    )

                fig_gordura = formatar_eixo_data(
                    fig_gordura
                )

                st.plotly_chart(
                    fig_gordura,
                    use_container_width=True,
                    config=CONFIG_GRAFICO_PACIENTE
                )


                # =====================================================
                # EVOLUÇÃO DA ÁGUA CORPORAL
                # =====================================================

                st.write(
                    "## 💧 Evolução da água corporal"
                )

                fig_agua = px.line(
                    df,
                    x="Data",
                    y="Água",
                    markers=True,
                    labels={
                        "Data": "Data",
                        "Água": "Água corporal (%)"
                    }
                )

                fig_agua.update_layout(
                    xaxis_title="",
                    yaxis_title="Água corporal (%)"
                )

                if referencias["agua"]:

                    # A BF1000 classifica valores acima desta faixa
                    # como "muito bons"; por isso não adicionamos
                    # uma zona de alerta acima da faixa sombreada.
                    fig_agua = adicionar_faixa_referencia(
                        fig_agua,
                        referencias["agua"][0],
                        referencias["agua"][1]
                    )

                fig_agua = formatar_eixo_data(
                    fig_agua
                )

                st.plotly_chart(
                    fig_agua,
                    use_container_width=True,
                    config=CONFIG_GRAFICO_PACIENTE
                )


                # =====================================================
                # EVOLUÇÃO MUSCULAR
                # =====================================================

                st.write(
                    "## 💪 Evolução muscular"
                )

                fig_musculo = px.line(
                    df,
                    x="Data",
                    y="Músculo",
                    markers=True,
                    labels={
                        "Data": "Data",
                        "Músculo": "Músculo (%)"
                    }
                )

                fig_musculo.update_layout(
                    xaxis_title="",
                    yaxis_title="Músculo (%)"
                )

                if referencias["musculo"]:

                    fig_musculo = adicionar_faixa_referencia(
                        fig_musculo,
                        referencias["musculo"][0],
                        referencias["musculo"][1]
                    )

                fig_musculo = formatar_eixo_data(
                    fig_musculo
                )

                st.plotly_chart(
                    fig_musculo,
                    use_container_width=True,
                    config=CONFIG_GRAFICO_PACIENTE
                )


                # =====================================================
                # EVOLUÇÃO DA GORDURA VISCERAL
                # =====================================================

                st.write(
                    "## 🫀 Evolução da gordura visceral"
                )

                fig_visceral = px.line(
                    df,
                    x="Data",
                    y="Gordura visceral",
                    markers=True,
                    labels={
                        "Data": "Data",
                        "Gordura visceral": "Gordura visceral"
                    }
                )

                fig_visceral.update_layout(
                    xaxis_title="",
                    yaxis_title="Gordura visceral"
                )

                if referencias["gordura_visceral"]:

                    fig_visceral = adicionar_faixa_referencia(
                        fig_visceral,
                        referencias["gordura_visceral"][0],
                        referencias["gordura_visceral"][1]
                    )

                fig_visceral = formatar_eixo_data(
                    fig_visceral
                )

                st.plotly_chart(
                    fig_visceral,
                    use_container_width=True,
                    config=CONFIG_GRAFICO_PACIENTE
                )


                st.divider()

                st.write(
                    "## 📋 Histórico"
                )

                dados_historico = []

                for p in reversed(
                    pesagens_paciente
                ):

                    dados_historico.append(
                        {
                            "Data": p["data"],
                            "Peso (kg)": p["peso_kg"],
                            "IMC": p["imc"],
                            "Gordura (%)": p["gordura_pct"],
                            "Músculo (%)": p["musculo_pct"],
                            "Cintura (cm)": p["cintura_cm"],
                        }
                    )

                st.dataframe(
                    dados_historico,
                    use_container_width=True,
                    hide_index=True
                )

        except Exception as erro:

            st.error(
                "Não foi possível carregar as avaliações."
            )

            st.exception(erro)


# =========================================================
# ÁREA PROFISSIONAL
# =========================================================

elif st.session_state.get("area") == "profissional":

    st.subheader(
        "🩺 Área Profissional"
    )

    if not st.session_state.get(
        "profissional_logado",
        False
    ):

        senha = st.text_input(
            "Senha profissional",
            type="password"
        )

        if st.button(
            "Entrar",
            type="primary",
            use_container_width=True
        ):

            if (
                senha
                == st.secrets[
                    "senha_profissional"
                ]
            ):

                st.session_state[
                    "profissional_logado"
                ] = True

                st.rerun()

            else:

                st.error(
                    "Senha incorreta."
                )

        if st.button("← Voltar"):

            st.session_state[
                "area"
            ] = None

            st.rerun()


    # =====================================================
    # LOGADO
    # =====================================================

    else:

        col_status, col_sair = st.columns(
            [4, 1]
        )

        with col_status:

            st.success(
                "Acesso profissional autorizado."
            )

        with col_sair:

            if st.button(
                "Sair",
                key="sair_profissional",
                use_container_width=True
            ):

                st.session_state[
                    "profissional_logado"
                ] = False

                st.session_state[
                    "area"
                ] = None

                st.rerun()

        st.divider()

        st.write(
            "### Menu profissional"
        )

        if (
            "menu_profissional"
            not in st.session_state
        ):

            st.session_state[
                "menu_profissional"
            ] = "Nova pesagem"

        if st.button(
            "⚖️ Nova pesagem",
            use_container_width=True
        ):

            st.session_state[
                "menu_profissional"
            ] = "Nova pesagem"

        if st.button(
            "➕ Cadastrar paciente",
            use_container_width=True
        ):

            st.session_state[
                "menu_profissional"
            ] = "Cadastrar paciente"

        if st.button(
            "🔎 Consultar pacientes",
            use_container_width=True
        ):

            st.session_state[
                "menu_profissional"
            ] = "Consultar pacientes"

        if st.button(
            "📈 Histórico",
            use_container_width=True
        ):

            st.session_state[
                "menu_profissional"
            ] = "Histórico"

        if st.button(
            "✏️ Editar / excluir pesagem",
            use_container_width=True
        ):

            st.session_state[
                "menu_profissional"
            ] = "Editar pesagem"

        opcao = st.session_state[
            "menu_profissional"
        ]

        st.divider()


        # =================================================
        # CADASTRAR PACIENTE
        # =================================================

        if opcao == "Cadastrar paciente":

            st.write(
                "### ➕ Cadastro de paciente"
            )

            nome = st.text_input(
                "Nome completo"
            )

            sexo = st.selectbox(
                "Sexo",
                [
                    "",
                    "Feminino",
                    "Masculino"
                ]
            )

            # CORREÇÃO DO LIMITE DE DATA
            nascimento = st.date_input(
                "Data de nascimento",
                value=None,
                min_value=date(1900,1,1),
                max_value=date.today(),
                format="DD/MM/YYYY"
            )

            altura = st.number_input(
                "Altura (cm)",
                min_value=0.0,
                max_value=250.0,
                step=0.1
            )

            nivel_atividade = st.selectbox(
                "Nível de atividade",
                [
                    "",
                    "Sedentário",
                    "Leve",
                    "Moderado",
                    "Ativo",
                    "Muito ativo"
                ]
            )

            telefone = st.text_input(
                "Telefone"
            )

            email = st.text_input(
                "E-mail"
            )

        # =====================================================
        # DADOS DO CICLO MENSTRUAL / MENOPAUSA
        # =====================================================

            ultima_menstruacao = None
            ciclo_medio_dias = None
            menopausa = "NAO"

            if sexo == "Feminino":

                st.divider()

                st.write(
                    "#### 🌙 Situação menstrual"
                )

                st.caption(
                    "Preenchimento opcional. "
                    "A paciente também poderá atualizar "
                    "esses dados posteriormente."
                )

                menopausa_marcada = st.checkbox(
                    "Está na menopausa",
                    key="cadastro_menopausa"
                )

                if menopausa_marcada:

                    menopausa = "SIM"

                    st.caption(
                        "O portal exibirá permanentemente "
                        "A Sábia Anciã para esta paciente."
                    )

                else:

                    informar_ciclo = st.checkbox(
                        "Cadastrar dados do ciclo agora"
                    )

                    if informar_ciclo:

                        ultima_menstruacao = st.date_input(
                            "Data da última menstruação",
                            value=date.today(),
                            min_value=date(1900, 1, 1),
                            max_value=date.today(),
                            format="DD/MM/YYYY"
                        )

                        ciclo_medio_dias = st.number_input(
                            "Duração média do ciclo (dias)",
                            min_value=14,
                            max_value=50,
                            value=28,
                            step=1
                        )

            # =====================================================
            # BOTÃO DE CADASTRO
            # =====================================================

            if st.button(
                "Cadastrar paciente",
                type="primary",
                use_container_width=True
            ):

                if not nome.strip():

                    st.warning(
                        "Informe o nome do paciente."
                    )


                elif nascimento is None:

                    st.warning(
                        "Informe a data de nascimento."
                    )

                elif altura <= 0:

                    st.warning(
                        "Informe uma altura válida."
                    )

                else:

                    try:

                        novo_id = gerar_id_paciente(
                            pacientes
                        )

                        novo_codigo = (
                            gerar_codigo_acesso(
                                nome,
                                nascimento,
                                pacientes
                            )
                        )

                        novo_paciente = {
                            "id_paciente": novo_id,
                            "nome": nome.strip(),
                            "codigo_acesso": novo_codigo,
                            "sexo": sexo,
                            "nascimento":
                                nascimento.strftime(
                                    "%d/%m/%Y"
                                ),
                            "altura_cm": altura,
                            "nivel_atividade":
                                nivel_atividade,
                            "telefone":
                                telefone.strip(),
                            "email":
                                email.strip(),
                            "data_cadastro":
                                date.today().strftime(
                                    "%d/%m/%Y"
                                ),
                            "ativo": "SIM", 

                            "ultima_menstruacao": (
                                ultima_menstruacao.strftime(
                                    "%d/%m/%Y"
                                )
                                if ultima_menstruacao
                                else ""
                            ),

                            "ciclo_medio_dias": (
                                int(ciclo_medio_dias)
                                if ciclo_medio_dias
                                else ""
                            ),

                            "menopausa": menopausa,
                        }
                        

                        adicionar_paciente(
                            novo_paciente
                        )

                        st.success(
                            "Paciente cadastrado com sucesso!"
                        )

                        st.write(
                            f"**Paciente:** {nome}"
                        )

                        st.write(
                            f"**Código de acesso:** "
                            f"`{novo_codigo}`"
                        )

                        st.write(
                            f"**ID:** `{novo_id}`"
                        )

                    except Exception as erro:

                        st.error(
                            "Erro ao cadastrar paciente."
                        )

                        st.exception(erro)


        # =================================================
        # CONSULTAR PACIENTES
        # =================================================

        elif opcao == "Consultar pacientes":

            st.write(
                "### 🔎 Consultar pacientes"
            )

            busca = st.text_input(
                "Pesquisar pelo nome"
            )

            if busca:

                encontrados = [
                    p
                    for p in pacientes
                    if busca.lower()
                    in str(
                        p.get("nome", "")
                    ).lower()
                ]

            else:

                encontrados = pacientes

            for paciente in encontrados:

                st.divider()

                st.write(
                    f"### {paciente['nome']}"
                )

                st.write(
                    f"**Código:** "
                    f"`{paciente['codigo_acesso']}`"
                )

                st.write(
                    f"**Nascimento:** "
                    f"{paciente.get('nascimento', '-')}"
                )

                st.write(
                    f"**Telefone:** "
                    f"{paciente.get('telefone', '-')}"
                )


        # =================================================
        # NOVA PESAGEM
        # =================================================

        elif opcao == "Nova pesagem":

            st.write(
                "### ⚖️ Nova pesagem"
            )

            opcoes = {
                f"{p['nome']} - {p['id_paciente']}": p
                for p in pacientes
            }

            if not opcoes:

                st.warning(
                    "Nenhum paciente cadastrado."
                )

            else:

                escolha = st.selectbox(
                    "Paciente",
                    list(opcoes.keys())
                )

                paciente = opcoes[
                    escolha
                ]

                data_pesagem = st.date_input(
                    "Data da avaliação",
                    value=date.today(),
                    format="DD/MM/YYYY"
                )

                st.write(
                    "#### Bioimpedância"
                )

                peso = st.number_input(
                    "Peso (kg)",
                    min_value=0.0,
                    step=0.1
                )

                imc = st.number_input(
                    "IMC",
                    min_value=0.0,
                    step=0.1
                )

                gordura = st.number_input(
                    "Gordura corporal (%)",
                    min_value=0.0,
                    step=0.1
                )

                agua = st.number_input(
                    "Água corporal (%)",
                    min_value=0.0,
                    step=0.1
                )

                musculo = st.number_input(
                    "Músculo (%)",
                    min_value=0.0,
                    step=0.1
                )

                massa_ossea = st.number_input(
                    "Massa óssea (kg)",
                    min_value=0.0,
                    step=0.1
                )

                gordura_visceral = st.number_input(
                    "Gordura visceral",
                    min_value=0.0,
                    step=0.1
                )

                gordura_abdominal = st.number_input(
                    "Gordura abdominal",
                    min_value=0.0,
                    step=0.1
                )

                st.write(
                    "#### Distribuição regional da gordura"
                )

                gordura_braco_direito = st.number_input(
                    "Gordura braço direito (%)",
                    min_value=0.0,
                    step=0.1
                )

                gordura_braco_esquerdo = st.number_input(
                    "Gordura braço esquerdo (%)",
                    min_value=0.0,
                    step=0.1
                )

                gordura_perna_direita = st.number_input(
                    "Gordura perna direita (%)",
                    min_value=0.0,
                    step=0.1
                )

                gordura_perna_esquerda = st.number_input(
                    "Gordura perna esquerda (%)",
                    min_value=0.0,
                    step=0.1
                )

                bmr = st.number_input(
                    "BMR (kcal)",
                    min_value=0,
                    step=1
                )

                amr = st.number_input(
                    "AMR (kcal)",
                    min_value=0,
                    step=1
                )

                st.write(
                    "#### Medidas corporais"
                )

                cintura = st.number_input(
                    "Cintura (cm)",
                    min_value=0.0,
                    step=0.1
                )

                abdomen = st.number_input(
                    "Abdômen (cm)",
                    min_value=0.0,
                    step=0.1
                )

                quadril = st.number_input(
                    "Quadril (cm)",
                    min_value=0.0,
                    step=0.1
                )

                braco = st.number_input(
                    "Braço (cm)",
                    min_value=0.0,
                    step=0.1
                )

                coxa = st.number_input(
                    "Coxa (cm)",
                    min_value=0.0,
                    step=0.1
                )

                observacoes = st.text_area(
                    "Comentário para o paciente"
                )

                if st.button(
                    "💾 Salvar pesagem",
                    type="primary",
                    use_container_width=True
                ):

                    if peso <= 0:

                        st.warning(
                            "Informe o peso."
                        )

                    else:

                        pesagens = (
                            listar_pesagens()
                        )

                        nova = {
                            "id_pesagem":
                                gerar_id_pesagem(
                                    pesagens
                                ),
                            "id_paciente":
                                paciente[
                                    "id_paciente"
                                ],
                            "data":
                                data_pesagem.strftime(
                                    "%d/%m/%Y"
                                ),
                            "peso_kg": peso,
                            "imc": imc,
                            "gordura_pct": gordura,
                            "agua_pct": agua,
                            "musculo_pct": musculo,
                            "massa_ossea_kg":
                                massa_ossea,
                            "gordura_visceral":
                                gordura_visceral,
                            "gordura_abdominal":
                                gordura_abdominal,
                            "bmr_kcal": bmr,
                            "amr_kcal": amr,
                            "cintura_cm": cintura,
                            "abdomen_cm": abdomen,
                            "quadril_cm": quadril,
                            "braco_cm": braco,
                            "coxa_cm": coxa,
                            "observacoes":
                                observacoes.strip(),
                            "gordura_braco_direito_pct":
                                gordura_braco_direito,
                            "gordura_braco_esquerdo_pct":
                                gordura_braco_esquerdo,
                            "gordura_perna_direita_pct":
                                gordura_perna_direita,
                            "gordura_perna_esquerda_pct":
                                gordura_perna_esquerda
                        }

                        adicionar_pesagem(
                            nova
                        )

                        st.success(
                            "Pesagem registrada com sucesso!"
                        )


        # =================================================
        # HISTÓRICO
        # =================================================

        elif opcao == "Histórico":

            st.write(
                "### 📈 Histórico"
            )

            opcoes = {
                f"{p['nome']} - {p['id_paciente']}": p
                for p in pacientes
            }

            if opcoes:

                escolha = st.selectbox(
                    "Paciente",
                    list(opcoes.keys()),
                    key="historico_prof"
                )

                paciente = opcoes[
                    escolha
                ]

                pesagens = (
                    listar_pesagens_por_paciente(
                        paciente[
                            "id_paciente"
                        ]
                    )
                )

                pesagens = sorted(
                    pesagens,
                    key=lambda p: converter_data(
                        p["data"]
                    ),
                    reverse=True
                )

                st.dataframe(
                    pesagens,
                    use_container_width=True,
                    hide_index=True
                )


        # =================================================
        # EDITAR / EXCLUIR PESAGEM
        # =================================================

        elif opcao == "Editar pesagem":

            st.write(
                "### ✏️ Editar ou excluir pesagem"
            )

            opcoes_pacientes = {
                f"{p['nome']} - {p['id_paciente']}": p
                for p in pacientes
            }

            if not opcoes_pacientes:

                st.warning(
                    "Nenhum paciente cadastrado."
                )

            else:

                escolha_paciente = st.selectbox(
                    "Paciente",
                    list(
                        opcoes_pacientes.keys()
                    ),
                    key="editar_paciente"
                )

                paciente = (
                    opcoes_pacientes[
                        escolha_paciente
                    ]
                )

                pesagens = (
                    listar_pesagens_por_paciente(
                        paciente[
                            "id_paciente"
                        ]
                    )
                )

                pesagens = sorted(
                    pesagens,
                    key=lambda p: converter_data(
                        p["data"]
                    ),
                    reverse=True
                )

                if not pesagens:

                    st.info(
                        "Este paciente não possui pesagens."
                    )

                else:

                    opcoes_pesagem = {
                        (
                            f"{p['data']} | "
                            f"{p['peso_kg']} kg | "
                            f"{p['id_pesagem']}"
                        ): p
                        for p in pesagens
                    }

                    escolha_pesagem = (
                        st.selectbox(
                            "Selecione a pesagem",
                            list(
                                opcoes_pesagem.keys()
                            ),
                            key="pesagem_edicao"
                        )
                    )

                    registro = (
                        opcoes_pesagem[
                            escolha_pesagem
                        ]
                    )

                    st.caption(
                        f"ID da avaliação: "
                        f"{registro['id_pesagem']}"
                    )

                    data_editada = st.date_input(
                        "Data da avaliação",
                        value=converter_data_para_date(
                            registro["data"]
                        ),
                        format="DD/MM/YYYY",
                        key="edit_data"
                    )

                    peso = st.number_input(
                        "Peso (kg)",
                        value=converter_numero(
                            registro["peso_kg"]
                        ),
                        step=0.1,
                        key="edit_peso"
                    )

                    imc = st.number_input(
                        "IMC",
                        value=converter_numero(
                            registro["imc"]
                        ),
                        step=0.1,
                        key="edit_imc"
                    )

                    gordura = st.number_input(
                        "Gordura corporal (%)",
                        value=converter_numero(
                            registro[
                                "gordura_pct"
                            ]
                        ),
                        step=0.1,
                        key="edit_gordura"
                    )

                    agua = st.number_input(
                        "Água corporal (%)",
                        value=converter_numero(
                            registro[
                                "agua_pct"
                            ]
                        ),
                        step=0.1,
                        key="edit_agua"
                    )

                    musculo = st.number_input(
                        "Músculo (%)",
                        value=converter_numero(
                            registro[
                                "musculo_pct"
                            ]
                        ),
                        step=0.1,
                        key="edit_musculo"
                    )

                    massa_ossea = st.number_input(
                        "Massa óssea (kg)",
                        value=converter_numero(
                            registro[
                                "massa_ossea_kg"
                            ]
                        ),
                        step=0.1,
                        key="edit_ossea"
                    )

                    gordura_visceral = st.number_input(
                        "Gordura visceral",
                        value=converter_numero(
                            registro[
                                "gordura_visceral"
                            ]
                        ),
                        step=0.1,
                        key="edit_visceral"
                    )

                    gordura_abdominal = st.number_input(
                        "Gordura abdominal",
                        value=converter_numero(
                            registro[
                                "gordura_abdominal"
                            ]
                        ),
                        step=0.1,
                        key="edit_abdominal"
                    )

                    st.write(
                        "#### Distribuição regional da gordura"
                    )

                    gordura_braco_direito = st.number_input(
                        "Gordura braço direito (%)",
                        value=converter_numero(
                            registro.get(
                                "gordura_braco_direito_pct",
                                ""
                            )
                        ),
                        step=0.1,
                        key="edit_gordura_braco_direito"
                    )

                    gordura_braco_esquerdo = st.number_input(
                        "Gordura braço esquerdo (%)",
                        value=converter_numero(
                            registro.get(
                                "gordura_braco_esquerdo_pct",
                                ""
                            )
                        ),
                        step=0.1,
                        key="edit_gordura_braco_esquerdo"
                    )

                    gordura_perna_direita = st.number_input(
                        "Gordura perna direita (%)",
                        value=converter_numero(
                            registro.get(
                                "gordura_perna_direita_pct",
                                ""
                            )
                        ),
                        step=0.1,
                        key="edit_gordura_perna_direita"
                    )

                    gordura_perna_esquerda = st.number_input(
                        "Gordura perna esquerda (%)",
                        value=converter_numero(
                            registro.get(
                                "gordura_perna_esquerda_pct",
                                ""
                            )
                        ),
                        step=0.1,
                        key="edit_gordura_perna_esquerda"
                    )

                    bmr = st.number_input(
                        "BMR (kcal)",
                        value=converter_inteiro(
                            registro[
                                "bmr_kcal"
                            ]
                        ),
                        step=1,
                        key="edit_bmr"
                    )

                    amr = st.number_input(
                        "AMR (kcal)",
                        value=converter_inteiro(
                            registro[
                                "amr_kcal"
                            ]
                        ),
                        step=1,
                        key="edit_amr"
                    )

                    st.write(
                        "#### Medidas corporais"
                    )

                    cintura = st.number_input(
                        "Cintura (cm)",
                        value=converter_numero(
                            registro[
                                "cintura_cm"
                            ]
                        ),
                        step=0.1,
                        key="edit_cintura"
                    )

                    abdomen = st.number_input(
                        "Abdômen (cm)",
                        value=converter_numero(
                            registro[
                                "abdomen_cm"
                            ]
                        ),
                        step=0.1,
                        key="edit_abdomen"
                    )

                    quadril = st.number_input(
                        "Quadril (cm)",
                        value=converter_numero(
                            registro[
                                "quadril_cm"
                            ]
                        ),
                        step=0.1,
                        key="edit_quadril"
                    )

                    braco = st.number_input(
                        "Braço (cm)",
                        value=converter_numero(
                            registro[
                                "braco_cm"
                            ]
                        ),
                        step=0.1,
                        key="edit_braco"
                    )

                    coxa = st.number_input(
                        "Coxa (cm)",
                        value=converter_numero(
                            registro[
                                "coxa_cm"
                            ]
                        ),
                        step=0.1,
                        key="edit_coxa"
                    )

                    observacoes = st.text_area(
                        "Comentário para o paciente",
                        value=str(
                            registro.get(
                                "observacoes",
                                ""
                            )
                        ),
                        key="edit_observacoes"
                    )

                    st.divider()

                    if st.button(
                        "💾 Salvar alterações",
                        type="primary",
                        use_container_width=True
                    ):

                        atualizado = {
                            "id_pesagem":
                                registro[
                                    "id_pesagem"
                                ],
                            "id_paciente":
                                registro[
                                    "id_paciente"
                                ],
                            "data":
                                data_editada.strftime(
                                    "%d/%m/%Y"
                                ),
                            "peso_kg": peso,
                            "imc": imc,
                            "gordura_pct": gordura,
                            "agua_pct": agua,
                            "musculo_pct":
                                musculo,
                            "massa_ossea_kg":
                                massa_ossea,
                            "gordura_visceral":
                                gordura_visceral,
                            "gordura_abdominal":
                                gordura_abdominal,
                            "bmr_kcal": bmr,
                            "amr_kcal": amr,
                            "cintura_cm": cintura,
                            "abdomen_cm": abdomen,
                            "quadril_cm": quadril,
                            "braco_cm": braco,
                            "coxa_cm": coxa,
                            "observacoes":
                                observacoes.strip(),
                            "gordura_braco_direito_pct":
                                gordura_braco_direito,
                            "gordura_braco_esquerdo_pct":
                                gordura_braco_esquerdo,
                            "gordura_perna_direita_pct":
                                gordura_perna_direita,
                            "gordura_perna_esquerda_pct":
                                gordura_perna_esquerda
                        }

                        if editar_pesagem(
                            registro[
                                "id_pesagem"
                            ],
                            atualizado
                        ):

                            st.success(
                                "Pesagem atualizada com sucesso!"
                            )

                            st.rerun()

                        else:

                            st.error(
                                "Não foi possível localizar a pesagem."
                            )


                    # -------------------------------------
                    # EXCLUSÃO
                    # -------------------------------------

                    st.divider()

                    st.write(
                        "#### 🗑️ Excluir avaliação"
                    )

                    st.warning(
                        "A exclusão remove definitivamente "
                        "esta avaliação do histórico."
                    )

                    confirmar = st.checkbox(
                        "Confirmo que desejo excluir esta pesagem",
                        key="confirmar_exclusao"
                    )

                    if st.button(
                        "🗑️ Excluir pesagem",
                        disabled=not confirmar,
                        use_container_width=True
                    ):

                        if excluir_pesagem(
                            registro[
                                "id_pesagem"
                            ]
                        ):

                            st.success(
                                "Pesagem excluída com sucesso."
                            )

                            st.rerun()

                        else:

                            st.error(
                                "Não foi possível localizar a pesagem."
                            )