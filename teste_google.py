import gspread

gc = gspread.oauth(
    credentials_filename="client_secret.json"
)

planilha = gc.open("Controle de Avaliação Corporal")

print("Planilha encontrada!")
print("Abas disponíveis:")

for aba in planilha.worksheets():
    print("-", aba.title)