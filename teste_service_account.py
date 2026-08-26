import gspread

gc = gspread.service_account(
    filename="service_account.json"
)

planilha = gc.open(
    "Controle de Avaliação Corporal"
)

print("Conexão com Service Account funcionando!")
print("Abas encontradas:")

for aba in planilha.worksheets():
    print("-", aba.title)