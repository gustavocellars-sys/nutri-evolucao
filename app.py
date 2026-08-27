import os
import random
import string

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
)


# =========================================================
# IDENTIDADE PROFISSIONAL
# =========================================================

NOME_PROFISSIONAL = "Nutricionista Andrea Cella"
SUBTITULO_APP = "Acompanhamento de evolução corporal"


# =========================================================
# CONFIGURAÇÃO DA PÁGINA
# =========================================================

st.set_page_config(
    page_title=NOME_PROFISSIONAL,
    page_icon="🥗",
    layout="centered",
)


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

def gerar_codigo_acesso(pacientes):
    caracteres = string.ascii_uppercase + string.digits

    codigos_existentes = {
        str(paciente.get("codigo_acesso", "")).upper()
        for paciente in pacientes
    }

    while True:
        codigo = "".join(
            random.choices(caracteres, k=6)
        )

        if codigo not in codigos_existentes:
            return codigo


def gerar_id_paciente(pacientes):
    numeros = []

    for paciente in pacientes:
        id_atual = str(
            paciente.get("id_paciente", "")
        )

        try:
            numero = int(
                id_atual.replace("P", "")
            )
            numeros.append(numero)

        except ValueError:
            pass

    if not numeros:
        return "P0001"

    proximo_numero = max(numeros) + 1

    return f"P{proximo_numero:04d}"


def gerar_id_pesagem(pesagens):
    numeros = []

    for pesagem in pesagens:
        id_atual = str(
            pesagem.get("id_pesagem", "")
        )

        try:
            numero = int(
                id_atual.replace("AV", "")
            )
            numeros.append(numero)

        except ValueError:
            pass

    if not numeros:
        return "AV0001"

    proximo_numero = max(numeros) + 1

    return f"AV{proximo_numero:04d}"


def buscar_paciente_por_codigo(codigo, pacientes):
    codigo = codigo.strip().upper()

    for paciente in pacientes:
        codigo_paciente = str(
            paciente.get("codigo_acesso", "")
        ).strip().upper()

        if codigo_paciente == codigo:
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


def converter_data(data_texto):
    try:
        return datetime.strptime(
            str(data_texto),
            "%d/%m/%Y",
        )

    except ValueError:
        return datetime.min


def formatar_numero(numero, casas=1):
    return f"{numero:.{casas}f}".replace(".", ",")


# =========================================================
# GRÁFICOS PARA PDF
# =========================================================

def criar_grafico_pdf(
    pesagens,
    campo,
    titulo,
    unidade,
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
        marker="o",
    )

    ax.set_title(titulo)
    ax.set_ylabel(unidade)

    ax.grid(
        True,
        alpha=0.25,
    )

    plt.xticks(
        rotation=30,
        ha="right",
    )

    plt.tight_layout()

    imagem = BytesIO()

    fig.savefig(
        imagem,
        format="png",
        dpi=150,
        bbox_inches="tight",
    )

    plt.close(fig)

    imagem.seek(0)

    return imagem


# =========================================================
# GERAR PDF DO PACIENTE
# =========================================================

def gerar_pdf_paciente(
    paciente,
    pesagens,
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

    # LOGOTIPO
    if os.path.exists("logo.png"):
        elementos.append(
            Image(
                "logo.png",
                width=5 * cm,
                height=2.5 * cm,
            )
        )

        elementos.append(
            Spacer(
                1,
                0.4 * cm,
            )
        )

    elementos.append(
        Paragraph(
            NOME_PROFISSIONAL,
            estilos["Title"],
        )
    )

    elementos.append(
        Paragraph(
            "Relatório de evolução corporal",
            estilos["Heading2"],
        )
    )

    elementos.append(
        Spacer(
            1,
            0.5 * cm,
        )
    )

    elementos.append(
        Paragraph(
            f"<b>Paciente:</b> {paciente['nome']}",
            estilos["Normal"],
        )
    )

    elementos.append(
        Paragraph(
            f"<b>Data do relatório:</b> "
            f"{date.today().strftime('%d/%m/%Y')}",
            estilos["Normal"],
        )
    )

    elementos.append(
        Spacer(
            1,
            0.7 * cm,
        )
    )

    ultima = pesagens[-1]

    # -----------------------------------------------------
    # ÚLTIMA AVALIAÇÃO
    # -----------------------------------------------------

    elementos.append(
        Paragraph(
            "Última avaliação",
            estilos["Heading2"],
        )
    )

    dados_ultima = [
        ["Indicador", "Resultado"],
        [
            "Data",
            ultima["data"],
        ],
        [
            "Peso",
            f"{ultima['peso_kg']} kg",
        ],
        [
            "IMC",
            ultima["imc"],
        ],
        [
            "Gordura corporal",
            f"{ultima['gordura_pct']} %",
        ],
        [
            "Água corporal",
            f"{ultima['agua_pct']} %",
        ],
        [
            "Músculo",
            f"{ultima['musculo_pct']} %",
        ],
        [
            "Massa óssea",
            f"{ultima['massa_ossea_kg']} kg",
        ],
        [
            "Gordura visceral",
            ultima["gordura_visceral"],
        ],
        [
            "Gordura abdominal",
            ultima["gordura_abdominal"],
        ],
        [
            "Cintura",
            f"{ultima['cintura_cm']} cm",
        ],
        [
            "Abdômen",
            f"{ultima['abdomen_cm']} cm",
        ],
        [
            "Quadril",
            f"{ultima['quadril_cm']} cm",
        ],
        [
            "Braço",
            f"{ultima['braco_cm']} cm",
        ],
        [
            "Coxa",
            f"{ultima['coxa_cm']} cm",
        ],
    ]

    tabela = Table(
        dados_ultima,
        colWidths=[
            8 * cm,
            8 * cm,
        ],
    )

    tabela.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#E8F2ED"),
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.3,
                    colors.lightgrey,
                ),
                (
                    "PADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
            ]
        )
    )

    elementos.append(tabela)

    elementos.append(
        Spacer(
            1,
            0.8 * cm,
        )
    )

    # -----------------------------------------------------
    # GRÁFICO PESO
    # -----------------------------------------------------

    grafico_peso = criar_grafico_pdf(
        pesagens,
        "peso_kg",
        "Evolução do peso",
        "kg",
    )

    elementos.append(
        Paragraph(
            "Evolução do peso",
            estilos["Heading2"],
        )
    )

    elementos.append(
        Image(
            grafico_peso,
            width=17 * cm,
            height=7 * cm,
        )
    )

    elementos.append(
        Spacer(
            1,
            0.5 * cm,
        )
    )

    # -----------------------------------------------------
    # GRÁFICO GORDURA
    # -----------------------------------------------------

    grafico_gordura = criar_grafico_pdf(
        pesagens,
        "gordura_pct",
        "Evolução da gordura corporal",
        "%",
    )

    elementos.append(
        Paragraph(
            "Evolução da gordura corporal",
            estilos["Heading2"],
        )
    )

    elementos.append(
        Image(
            grafico_gordura,
            width=17 * cm,
            height=7 * cm,
        )
    )

    elementos.append(
        Spacer(
            1,
            0.5 * cm,
        )
    )

    # -----------------------------------------------------
    # GRÁFICO MÚSCULO
    # -----------------------------------------------------

    grafico_musculo = criar_grafico_pdf(
        pesagens,
        "musculo_pct",
        "Evolução muscular",
        "%",
    )

    elementos.append(
        Paragraph(
            "Evolução muscular",
            estilos["Heading2"],
        )
    )

    elementos.append(
        Image(
            grafico_musculo,
            width=17 * cm,
            height=7 * cm,
        )
    )

    elementos.append(
        Spacer(
            1,
            0.7 * cm,
        )
    )

    # -----------------------------------------------------
    # HISTÓRICO
    # -----------------------------------------------------

    elementos.append(
        Paragraph(
            "Histórico de avaliações",
            estilos["Heading2"],
        )
    )

    dados_historico = [
        [
            "Data",
            "Peso",
            "IMC",
            "Gordura",
            "Músculo",
        ]
    ]

    for pesagem in reversed(
        pesagens
    ):
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
        repeatRows=1,
    )

    tabela_historico.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#E8F2ED"),
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.3,
                    colors.lightgrey,
                ),
                (
                    "ALIGN",
                    (1, 1),
                    (-1, -1),
                    "CENTER",
                ),
                (
                    "PADDING",
                    (0, 0),
                    (-1, -1),
                    5,
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
# CARREGAMENTO DOS PACIENTES
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

    col_logo1, col_logo2, col_logo3 = st.columns(
        [1, 2, 1]
    )

    with col_logo2:
        st.image(
            "logo.png",
            use_container_width=True,
        )

    st.markdown(
        f"""
        <div class="cabecalho-profissional">
            <p>{SUBTITULO_APP}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

else:

    st.markdown(
        f"""
        <div class="cabecalho-profissional">
            <h1>{NOME_PROFISSIONAL}</h1>
            <p>{SUBTITULO_APP}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# TELA INICIAL
# =========================================================

if not st.session_state.get("area"):

    st.write(
        "Acesse seus resultados de avaliações corporais."
    )

    st.write("")

    if st.button(
        "👤 ACESSAR COMO PACIENTE",
        type="primary",
        use_container_width=True,
    ):
        st.session_state["area"] = "paciente"
        st.rerun()

    st.caption(
        "Utilize o código de identificação fornecido pela nutricionista."
    )

    st.write("")
    st.write("")
    st.divider()

    col_espaco, col_profissional = st.columns(
        [2, 1]
    )

    with col_profissional:

        if st.button(
            "🩺 Área profissional",
            use_container_width=True,
        ):
            st.session_state[
                "area"
            ] = "profissional"

            st.rerun()


# =========================================================
# ÁREA DO PACIENTE
# =========================================================

elif st.session_state.get("area") == "paciente":

    st.subheader(
        "👤 Área do Paciente"
    )

    # -----------------------------------------------------
    # LOGIN
    # -----------------------------------------------------

    if "paciente_logado_id" not in st.session_state:

        codigo = st.text_input(
            "Código de identificação",
            placeholder="Ex.: X7MP42",
        )

        if st.button(
            "Acessar meus resultados",
            type="primary",
            use_container_width=True,
        ):

            if not codigo:

                st.warning(
                    "Informe seu código de identificação."
                )

            else:

                paciente = buscar_paciente_por_codigo(
                    codigo,
                    pacientes,
                )

                if paciente:

                    st.session_state[
                        "paciente_logado_id"
                    ] = paciente["id_paciente"]

                    st.rerun()

                else:

                    st.error(
                        "Código não encontrado. "
                        "Confira o código informado."
                    )

        if st.button(
            "← Voltar",
        ):
            st.session_state[
                "area"
            ] = None

            st.rerun()


    # -----------------------------------------------------
    # PAINEL DO PACIENTE
    # -----------------------------------------------------

    else:

        paciente = buscar_paciente_por_id(
            st.session_state[
                "paciente_logado_id"
            ],
            pacientes,
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
                use_container_width=True,
            ):

                del st.session_state[
                    "paciente_logado_id"
                ]

                st.session_state[
                    "area"
                ] = None

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
                    ),
                )

                # -----------------------------------------
                # PDF
                # -----------------------------------------

                pdf = gerar_pdf_paciente(
                    paciente,
                    pesagens_paciente,
                )

                st.download_button(
                    label="📄 Baixar relatório em PDF",
                    data=pdf,
                    file_name=(
                        f"evolucao_"
                        f"{paciente['nome'].replace(' ', '_')}.pdf"
                    ),
                    mime="application/pdf",
                    use_container_width=True,
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

                imc_atual = converter_numero(
                    ultima["imc"]
                )

                # -----------------------------------------
                # ÚLTIMA AVALIAÇÃO
                # -----------------------------------------

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
                        delta_color="off",
                    )

                    st.metric(
                        "🔥 Gordura corporal",
                        f"{formatar_numero(
                            gordura_atual
                        )} %",
                        f"{formatar_numero(
                            gordura_atual -
                            gordura_inicial
                        )} p.p.",
                        delta_color="off",
                    )

                with col2:

                    st.metric(
                        "📐 IMC",
                        formatar_numero(
                            imc_atual
                        ),
                    )

                    st.metric(
                        "💪 Músculo",
                        f"{formatar_numero(
                            musculo_atual
                        )} %",
                        f"{formatar_numero(
                            musculo_atual -
                            musculo_inicial
                        )} p.p.",
                        delta_color="off",
                    )

                # -----------------------------------------
                # EVOLUÇÃO GERAL
                # -----------------------------------------

                st.divider()

                st.write(
                    "## Evolução geral"
                )

                st.write(
                    f"**Avaliações registradas:** "
                    f"{len(pesagens_paciente)}"
                )

                st.write(
                    f"**Primeira avaliação:** "
                    f"{primeira['data']}"
                )

                st.write(
                    f"**Última avaliação:** "
                    f"{ultima['data']}"
                )

                # -----------------------------------------
                # DATAFRAME
                # -----------------------------------------

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
                            "Gordura": converter_numero(
                                pesagem["gordura_pct"]
                            ),
                            "Músculo": converter_numero(
                                pesagem["musculo_pct"]
                            ),
                        }
                    )

                df = pd.DataFrame(
                    dados_grafico
                )

                # -----------------------------------------
                # GRÁFICO PESO
                # -----------------------------------------

                st.divider()

                st.write(
                    "## 📉 Evolução do peso"
                )

                fig_peso = px.line(
                    df,
                    x="Data",
                    y="Peso",
                    markers=True,
                    labels={
                        "Data": "Data",
                        "Peso": "Peso (kg)",
                    },
                )

                fig_peso.update_layout(
                    yaxis_title="Peso (kg)",
                    xaxis_title="",
                )

                st.plotly_chart(
                    fig_peso,
                    use_container_width=True,
                )

                # -----------------------------------------
                # GRÁFICO GORDURA
                # -----------------------------------------

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
                        "Gordura": "Gordura (%)",
                    },
                )

                fig_gordura.update_layout(
                    yaxis_title="Gordura (%)",
                    xaxis_title="",
                )

                st.plotly_chart(
                    fig_gordura,
                    use_container_width=True,
                )

                # -----------------------------------------
                # GRÁFICO MÚSCULO
                # -----------------------------------------

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
                        "Músculo": "Músculo (%)",
                    },
                )

                fig_musculo.update_layout(
                    yaxis_title="Músculo (%)",
                    xaxis_title="",
                )

                st.plotly_chart(
                    fig_musculo,
                    use_container_width=True,
                )

                # -----------------------------------------
                # HISTÓRICO
                # -----------------------------------------

                st.divider()

                st.write(
                    "## 📋 Histórico"
                )

                dados_historico = []

                for pesagem in reversed(
                    pesagens_paciente
                ):

                    dados_historico.append(
                        {
                            "Data":
                                pesagem["data"],

                            "Peso (kg)":
                                pesagem["peso_kg"],

                            "IMC":
                                pesagem["imc"],

                            "Gordura (%)":
                                pesagem["gordura_pct"],

                            "Músculo (%)":
                                pesagem["musculo_pct"],

                            "Cintura (cm)":
                                pesagem["cintura_cm"],
                        }
                    )

                st.dataframe(
                    dados_historico,
                    use_container_width=True,
                    hide_index=True,
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

    # -----------------------------------------------------
    # LOGIN PROFISSIONAL
    # -----------------------------------------------------

    if not st.session_state.get(
        "profissional_logado",
        False,
    ):

        st.write(
            "Acesso restrito ao profissional."
        )

        senha = st.text_input(
            "Senha profissional",
            type="password",
            placeholder="Digite sua senha",
        )

        if st.button(
            "Entrar",
            type="primary",
            use_container_width=True,
        ):

            try:

                senha_correta = st.secrets[
                    "senha_profissional"
                ]

            except Exception:

                st.error(
                    "A senha profissional não foi "
                    "configurada corretamente."
                )

                st.stop()

            if senha == senha_correta:

                st.session_state[
                    "profissional_logado"
                ] = True

                st.rerun()

            else:

                st.error(
                    "Senha incorreta."
                )

        if st.button(
            "← Voltar",
        ):

            st.session_state[
                "area"
            ] = None

            st.rerun()


    # -----------------------------------------------------
    # PROFISSIONAL AUTENTICADO
    # -----------------------------------------------------

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
                use_container_width=True,
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

        if "menu_profissional" not in st.session_state:

            st.session_state[
                "menu_profissional"
            ] = "Nova pesagem"

        if st.button(
            "⚖️ Nova pesagem",
            use_container_width=True,
        ):

            st.session_state[
                "menu_profissional"
            ] = "Nova pesagem"

        if st.button(
            "➕ Cadastrar paciente",
            use_container_width=True,
        ):

            st.session_state[
                "menu_profissional"
            ] = "Cadastrar paciente"

        if st.button(
            "🔎 Consultar pacientes",
            use_container_width=True,
        ):

            st.session_state[
                "menu_profissional"
            ] = "Consultar pacientes"

        if st.button(
            "📈 Histórico",
            use_container_width=True,
        ):

            st.session_state[
                "menu_profissional"
            ] = "Histórico"

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
                    "Masculino",
                ],
            )

            nascimento = st.date_input(
                "Data de nascimento",
                value=None,
            )

            altura = st.number_input(
                "Altura (cm)",
                min_value=0.0,
                max_value=250.0,
                step=0.1,
                format="%.1f",
            )

            nivel_atividade = st.selectbox(
                "Nível de atividade",
                [
                    "",
                    "Sedentário",
                    "Leve",
                    "Moderado",
                    "Ativo",
                    "Muito ativo",
                ],
            )

            telefone = st.text_input(
                "Telefone"
            )

            email = st.text_input(
                "E-mail"
            )

            if st.button(
                "Cadastrar paciente",
                type="primary",
                use_container_width=True,
            ):

                if not nome.strip():

                    st.warning(
                        "Informe o nome do paciente."
                    )

                elif altura <= 0:

                    st.warning(
                        "Informe uma altura válida."
                    )

                else:

                    novo_id = gerar_id_paciente(
                        pacientes
                    )

                    novo_codigo = gerar_codigo_acesso(
                        pacientes
                    )

                    novo_paciente = {
                        "id_paciente":
                            novo_id,

                        "nome":
                            nome.strip(),

                        "codigo_acesso":
                            novo_codigo,

                        "sexo":
                            sexo,

                        "nascimento":
                            (
                                nascimento.strftime(
                                    "%d/%m/%Y"
                                )
                                if nascimento
                                else ""
                            ),

                        "altura_cm":
                            altura,

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

                        "ativo":
                            "SIM",
                    }

                    try:

                        adicionar_paciente(
                            novo_paciente
                        )

                        st.success(
                            "Paciente cadastrado "
                            "com sucesso!"
                        )

                        st.write(
                            f"**Paciente:** "
                            f"{novo_paciente['nome']}"
                        )

                        st.write(
                            f"**ID interno:** "
                            f"`{novo_id}`"
                        )

                        st.write(
                            f"**Código de acesso:** "
                            f"`{novo_codigo}`"
                        )

                    except Exception as erro:

                        st.error(
                            "Erro ao cadastrar o paciente."
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
                    paciente
                    for paciente in pacientes
                    if busca.lower()
                    in str(
                        paciente.get(
                            "nome",
                            ""
                        )
                    ).lower()
                ]

            else:

                encontrados = pacientes

            if encontrados:

                st.write(
                    f"Pacientes encontrados: "
                    f"**{len(encontrados)}**"
                )

                for paciente in encontrados:

                    st.divider()

                    st.write(
                        f"### "
                        f"{paciente.get('nome', '')}"
                    )

                    st.write(
                        f"**Código de acesso:** "
                        f"`{paciente.get('codigo_acesso', '')}`"
                    )

                    st.write(
                        f"**ID:** "
                        f"`{paciente.get('id_paciente', '')}`"
                    )

                    st.write(
                        f"**Telefone:** "
                        f"{paciente.get('telefone', '-')}"
                    )

                    st.write(
                        f"**E-mail:** "
                        f"{paciente.get('email', '-')}"
                    )

                    st.write(
                        f"**Altura:** "
                        f"{paciente.get('altura_cm', '-')} cm"
                    )

            else:

                st.warning(
                    "Nenhum paciente encontrado."
                )


        # =================================================
        # NOVA PESAGEM
        # =================================================

        elif opcao == "Nova pesagem":

            st.write(
                "### ⚖️ Nova pesagem"
            )

            if not pacientes:

                st.warning(
                    "Nenhum paciente cadastrado."
                )

            else:

                opcoes_pacientes = {
                    f"{p['nome']} - "
                    f"{p['id_paciente']}": p
                    for p in pacientes
                }

                paciente_selecionado = (
                    st.selectbox(
                        "Paciente",
                        list(
                            opcoes_pacientes.keys()
                        ),
                    )
                )

                paciente = opcoes_pacientes[
                    paciente_selecionado
                ]

                data_pesagem = st.date_input(
                    "Data da avaliação",
                    value=date.today(),
                )

                st.write(
                    "#### Bioimpedância"
                )

                peso = st.number_input(
                    "Peso (kg)",
                    min_value=0.0,
                    step=0.1,
                )

                imc = st.number_input(
                    "IMC",
                    min_value=0.0,
                    step=0.1,
                )

                gordura = st.number_input(
                    "Gordura corporal (%)",
                    min_value=0.0,
                    step=0.1,
                )

                agua = st.number_input(
                    "Água corporal (%)",
                    min_value=0.0,
                    step=0.1,
                )

                musculo = st.number_input(
                    "Músculo (%)",
                    min_value=0.0,
                    step=0.1,
                )

                massa_ossea = st.number_input(
                    "Massa óssea (kg)",
                    min_value=0.0,
                    step=0.1,
                )

                gordura_visceral = st.number_input(
                    "Gordura visceral",
                    min_value=0.0,
                    step=0.1,
                )

                gordura_abdominal = st.number_input(
                    "Gordura abdominal",
                    min_value=0.0,
                    step=0.1,
                )

                bmr = st.number_input(
                    "BMR (kcal)",
                    min_value=0,
                    step=1,
                )

                amr = st.number_input(
                    "AMR (kcal)",
                    min_value=0,
                    step=1,
                )

                st.write(
                    "#### Medidas corporais"
                )

                cintura = st.number_input(
                    "Cintura (cm)",
                    min_value=0.0,
                    step=0.1,
                )

                abdomen = st.number_input(
                    "Abdômen (cm)",
                    min_value=0.0,
                    step=0.1,
                )

                quadril = st.number_input(
                    "Quadril (cm)",
                    min_value=0.0,
                    step=0.1,
                )

                braco = st.number_input(
                    "Braço (cm)",
                    min_value=0.0,
                    step=0.1,
                )

                coxa = st.number_input(
                    "Coxa (cm)",
                    min_value=0.0,
                    step=0.1,
                )

                observacoes = st.text_area(
                    "Observações"
                )

                if st.button(
                    "💾 Salvar pesagem",
                    type="primary",
                    use_container_width=True,
                ):

                    if peso <= 0:

                        st.warning(
                            "Informe o peso do paciente."
                        )

                    else:

                        try:

                            pesagens = listar_pesagens()

                            nova_pesagem = {
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

                                "peso_kg":
                                    peso,

                                "imc":
                                    imc,

                                "gordura_pct":
                                    gordura,

                                "agua_pct":
                                    agua,

                                "musculo_pct":
                                    musculo,

                                "massa_ossea_kg":
                                    massa_ossea,

                                "gordura_visceral":
                                    gordura_visceral,

                                "gordura_abdominal":
                                    gordura_abdominal,

                                "bmr_kcal":
                                    bmr,

                                "amr_kcal":
                                    amr,

                                "cintura_cm":
                                    cintura,

                                "abdomen_cm":
                                    abdomen,

                                "quadril_cm":
                                    quadril,

                                "braco_cm":
                                    braco,

                                "coxa_cm":
                                    coxa,

                                "observacoes":
                                    observacoes.strip(),
                            }

                            adicionar_pesagem(
                                nova_pesagem
                            )

                            st.success(
                                "Pesagem registrada "
                                "com sucesso!"
                            )

                            st.write(
                                f"**ID da avaliação:** "
                                f"`{nova_pesagem['id_pesagem']}`"
                            )

                            st.write(
                                f"**Paciente:** "
                                f"{paciente['nome']}"
                            )

                        except Exception as erro:

                            st.error(
                                "Erro ao salvar a pesagem."
                            )

                            st.exception(erro)


        # =================================================
        # HISTÓRICO PROFISSIONAL
        # =================================================

        elif opcao == "Histórico":

            st.write(
                "### 📈 Histórico"
            )

            if not pacientes:

                st.warning(
                    "Nenhum paciente cadastrado."
                )

            else:

                opcoes_pacientes = {
                    f"{p['nome']} - "
                    f"{p['id_paciente']}": p
                    for p in pacientes
                }

                paciente_selecionado = (
                    st.selectbox(
                        "Selecione o paciente",
                        list(
                            opcoes_pacientes.keys()
                        ),
                        key="historico_profissional",
                    )
                )

                paciente = opcoes_pacientes[
                    paciente_selecionado
                ]

                try:

                    pesagens = (
                        listar_pesagens_por_paciente(
                            paciente["id_paciente"]
                        )
                    )

                    if not pesagens:

                        st.info(
                            "Esse paciente ainda "
                            "não possui avaliações."
                        )

                    else:

                        pesagens = sorted(
                            pesagens,
                            key=lambda x: converter_data(
                                x.get("data", "")
                            ),
                            reverse=True,
                        )

                        dados = []

                        for pesagem in pesagens:

                            dados.append(
                                {
                                    "Data":
                                        pesagem["data"],

                                    "Peso (kg)":
                                        pesagem["peso_kg"],

                                    "IMC":
                                        pesagem["imc"],

                                    "Gordura (%)":
                                        pesagem[
                                            "gordura_pct"
                                        ],

                                    "Músculo (%)":
                                        pesagem[
                                            "musculo_pct"
                                        ],

                                    "Cintura (cm)":
                                        pesagem[
                                            "cintura_cm"
                                        ],
                                }
                            )

                        st.dataframe(
                            dados,
                            use_container_width=True,
                            hide_index=True,
                        )

                except Exception as erro:

                    st.error(
                        "Erro ao carregar o histórico."
                    )

                    st.exception(erro)