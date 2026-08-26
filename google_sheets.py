import os
import gspread
import streamlit as st

from google.oauth2.service_account import Credentials


NOME_PLANILHA = "Controle de Avaliação Corporal"

COLUNAS_PACIENTES = [
    "id_paciente",
    "nome",
    "codigo_acesso",
    "sexo",
    "nascimento",
    "altura_cm",
    "nivel_atividade",
    "telefone",
    "email",
    "data_cadastro",
    "ativo",
]

COLUNAS_PESAGENS = [
    "id_pesagem",
    "id_paciente",
    "data",
    "peso_kg",
    "imc",
    "gordura_pct",
    "agua_pct",
    "musculo_pct",
    "massa_ossea_kg",
    "gordura_visceral",
    "gordura_abdominal",
    "bmr_kcal",
    "amr_kcal",
    "cintura_cm",
    "abdomen_cm",
    "quadril_cm",
    "braco_cm",
    "coxa_cm",
    "observacoes",
]


def conectar_planilha():

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    # -----------------------------------------
    # AMBIENTE LOCAL
    # -----------------------------------------

    if os.path.exists("service_account.json"):

        credentials = Credentials.from_service_account_file(
            "service_account.json",
            scopes=scopes
        )

    # -----------------------------------------
    # STREAMLIT CLOUD
    # -----------------------------------------

    else:

        credentials = Credentials.from_service_account_info(
            {
                "type": st.secrets["gcp_service_account"]["type"],
                "project_id": st.secrets["gcp_service_account"]["project_id"],
                "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
                "private_key": st.secrets["gcp_service_account"]["private_key"],
                "client_email": st.secrets["gcp_service_account"]["client_email"],
                "client_id": st.secrets["gcp_service_account"]["client_id"],
                "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
                "token_uri": st.secrets["gcp_service_account"]["token_uri"],
                "auth_provider_x509_cert_url": st.secrets[
                    "gcp_service_account"
                ]["auth_provider_x509_cert_url"],
                "client_x509_cert_url": st.secrets[
                    "gcp_service_account"
                ]["client_x509_cert_url"],
            },
            scopes=scopes
        )

    gc = gspread.authorize(credentials)

    return gc.open(NOME_PLANILHA)


def obter_aba_pacientes():
    planilha = conectar_planilha()
    return planilha.worksheet("pacientes")


def obter_aba_pesagens():
    planilha = conectar_planilha()
    return planilha.worksheet("pesagens")


def listar_pacientes():
    aba = obter_aba_pacientes()

    valores = aba.get("A:K")

    if len(valores) <= 1:
        return []

    pacientes = []

    for linha in valores[1:]:

        while len(linha) < len(COLUNAS_PACIENTES):
            linha.append("")

        linha = linha[:len(COLUNAS_PACIENTES)]

        if not any(str(valor).strip() for valor in linha):
            continue

        paciente = dict(
            zip(COLUNAS_PACIENTES, linha)
        )

        pacientes.append(paciente)

    return pacientes


def adicionar_paciente(paciente):
    aba = obter_aba_pacientes()

    nova_linha = [
        paciente["id_paciente"],
        paciente["nome"],
        paciente["codigo_acesso"],
        paciente["sexo"],
        paciente["nascimento"],
        paciente["altura_cm"],
        paciente["nivel_atividade"],
        paciente["telefone"],
        paciente["email"],
        paciente["data_cadastro"],
        paciente["ativo"],
    ]

    aba.append_row(
        nova_linha,
        value_input_option="USER_ENTERED"
    )


def listar_pesagens():
    aba = obter_aba_pesagens()

    valores = aba.get("A:S")

    if len(valores) <= 1:
        return []

    pesagens = []

    for linha in valores[1:]:

        while len(linha) < len(COLUNAS_PESAGENS):
            linha.append("")

        linha = linha[:len(COLUNAS_PESAGENS)]

        if not any(str(valor).strip() for valor in linha):
            continue

        pesagem = dict(
            zip(COLUNAS_PESAGENS, linha)
        )

        pesagens.append(pesagem)

    return pesagens


def adicionar_pesagem(pesagem):
    aba = obter_aba_pesagens()

    nova_linha = [
        pesagem["id_pesagem"],
        pesagem["id_paciente"],
        pesagem["data"],
        pesagem["peso_kg"],
        pesagem["imc"],
        pesagem["gordura_pct"],
        pesagem["agua_pct"],
        pesagem["musculo_pct"],
        pesagem["massa_ossea_kg"],
        pesagem["gordura_visceral"],
        pesagem["gordura_abdominal"],
        pesagem["bmr_kcal"],
        pesagem["amr_kcal"],
        pesagem["cintura_cm"],
        pesagem["abdomen_cm"],
        pesagem["quadril_cm"],
        pesagem["braco_cm"],
        pesagem["coxa_cm"],
        pesagem["observacoes"],
    ]

    aba.append_row(
        nova_linha,
        value_input_option="USER_ENTERED"
    )


def listar_pesagens_por_paciente(id_paciente):
    pesagens = listar_pesagens()

    return [
        pesagem
        for pesagem in pesagens
        if str(
            pesagem.get("id_paciente", "")
        ).strip()
        == str(id_paciente).strip()
    ]