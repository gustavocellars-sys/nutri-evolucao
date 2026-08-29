import os
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

                st.divider()

                st.write(
                    "## 📉 Evolução do peso"
                )

                st.plotly_chart(
                    px.line(
                        df,
                        x="Data",
                        y="Peso",
                        markers=True
                    ),
                    use_container_width=True
                )

                st.write(
                    "## 🔥 Evolução da gordura corporal"
                )

                st.plotly_chart(
                    px.line(
                        df,
                        x="Data",
                        y="Gordura",
                        markers=True
                    ),
                    use_container_width=True
                )

                st.write(
                    "## 💪 Evolução muscular"
                )

                st.plotly_chart(
                    px.line(
                        df,
                        x="Data",
                        y="Músculo",
                        markers=True
                    ),
                    use_container_width=True
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
                min_value=date(
                    1900,
                    1,
                    1
                ),
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
                            "ativo": "SIM"
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
                    "Observações"
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
                                observacoes.strip()
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
                        "Observações",
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
                                observacoes.strip()
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