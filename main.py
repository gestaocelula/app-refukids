import flet as ft
import sqlite3
import random

# ==========================================
# CONFIGURAÇÃO DO BANCO DE DADOS
# ==========================================
def inicializar_banco():
    conn = sqlite3.connect("refukids.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS criancas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_crianca TEXT,
            nome_responsavel TEXT,
            whatsapp TEXT,
            senha TEXT,
            foto_entrada TEXT,
            sala TEXT,
            status_entregue TEXT DEFAULT 'Não',
            foto_saida TEXT
        )
    ''')
    try:
        cursor.execute("ALTER TABLE criancas ADD COLUMN sala TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE criancas ADD COLUMN status_entregue TEXT DEFAULT 'Não'")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE criancas ADD COLUMN foto_saida TEXT")
    except sqlite3.OperationalError:
        pass
        
    conn.commit()
    conn.close()

def main(page: ft.Page):
    inicializar_banco()

    page.title = "Refúkids - IEQ Timbó"
    page.horizontal_alignment = "center"
    page.scroll = "auto"
    
    escala_sala = ["Nenhuma sala selecionada"]
    caminho_foto_atual = [None] 

    def simular_foto(e):
        caminho_foto_atual[0] = "/armazenamento/foto_entrada.jpg"
        btn_foto.content = ft.Text("Foto de Entrada OK ✔️")
        btn_foto.bgcolor = "green"
        btn_foto.color = "white"
        page.update()

    # ==========================================
    # SELETOR DE SALAS E ENCERRAR SALA
    # ==========================================
    texto_botao_sala = ft.Text("Salas: Nenhuma", weight="bold", size=12)

    def mudar_sala(nova_sala):
        escala_sala[0] = nova_sala
        texto_botao_sala.value = f"Sala: {nova_sala}"
        dialogo_salas.open = False
        page.update()

    # Confirmação de segurança para apagar os dados da sala
    def executar_encerramento():
        sala_atual = escala_sala[0]
        if sala_atual != "Nenhuma sala selecionada":
            conn = sqlite3.connect("refukids.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM criancas WHERE sala = ?", (sala_atual,))
            conn.commit()
            conn.close()

        dialogo_confirmar_encerramento.open = False
        dialogo_salas.open = False
        escala_sala[0] = "Nenhuma sala selecionada"
        texto_botao_sala.value = "Salas: Nenhuma"
        carregar_listagem()
        page.update()

    dialogo_confirmar_encerramento = ft.AlertDialog(
        title=ft.Text("⚠️ Encerrar Sala"),
        content=ft.Text("Tem certeza que deseja apagar todos os registros e dados salvos desta sala? Esta ação não pode ser desfeita!"),
        actions=[
            ft.TextButton("CANCELAR", on_click=lambda e: setattr(dialogo_confirmar_encerramento, 'open', False) or page.update()),
            ft.ElevatedButton("SIM, APAGAR TUDO", bgcolor="red", color="white", on_click=lambda e: executar_encerramento()),
        ]
    )

    dialogo_salas = ft.AlertDialog(
        title=ft.Text("Qual sala você está?"),
        content=ft.Column([
            ft.TextButton("Refubabies", on_click=lambda e: mudar_sala("Refubabies")),
            ft.TextButton("Refukids 1", on_click=lambda e: mudar_sala("Refukids 1")),
            ft.TextButton("Refukids 2", on_click=lambda e: mudar_sala("Refukids 2")),
            ft.TextButton("Refuteens", on_click=lambda e: mudar_sala("Refuteens")),
            ft.Divider(),
            ft.TextButton("Encerrar sala", on_click=lambda e: setattr(dialogo_confirmar_encerramento, 'open', True) or page.update(), style=ft.ButtonStyle(color="red")),
        ], tight=True),
        actions=[ft.TextButton("Cancelar", on_click=lambda e: setattr(dialogo_salas, 'open', False) or page.update())]
    )

    # ==========================================
    # CAMPOS DO FORMULÁRIO (ADICIONAR)
    # ==========================================
    campo_nome_crianca = ft.TextField(label="Nome da criança", width=300, border_radius=8)
    campo_nome_responsavel = ft.TextField(label="Nome do responsável", width=300, border_radius=8)
    campo_wpp_responsavel = ft.TextField(label="Wpp do responsável", width=300, border_radius=8, keyboard_type="phone")

    btn_foto = ft.ElevatedButton(
        content=ft.Text("Tirar foto da entrada"), 
        width=300, 
        height=50,
        on_click=simular_foto
    )

    # ==========================================
    # DIÁLOGO DE ENTREGA (FOTO DE SAÍDA)
    # ==========================================
    dialogo_entrega = ft.AlertDialog(
        title=ft.Text("Entregar criança"),
        content=ft.Text("Deseja bater uma foto do responsável que buscou?"),
        actions=[
            ft.TextButton("NÃO", on_click=lambda e: confirmar_entrega(False)),
            ft.TextButton("SIM", on_click=lambda e: confirmar_entrega(True)),
        ]
    )

    crianca_selecionada_id = [None]

    def abrir_pergunta_entrega(c_id):
        crianca_selecionada_id[0] = c_id
        dialogo_detalhes.open = False 
        dialogo_entrega.open = True  
        page.update()

    def confirmar_entrega(com_foto):
        c_id = crianca_selecionada_id[0]
        foto_saida_path = "/armazenamento/foto_saida_responsavel.jpg" if com_foto else None

        conn = sqlite3.connect("refukids.db")
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE criancas 
            SET status_entregue = 'Sim', foto_saida = ? 
            WHERE id = ?
        ''', (foto_saida_path, c_id))
        conn.commit()
        conn.close()

        dialogo_entrega.open = False
        carregar_listagem(campo_pesquisa.value)
        page.update()

    # ==========================================
    # DIÁLOGO DE DETALHES
    # ==========================================
    dialogo_detalhes = ft.AlertDialog(
        title=ft.Text("Detalhes da Criança"),
        content=ft.Column([], tight=True),
        actions=[ft.TextButton("FECHAR", on_click=lambda e: fechar_detalhes(e))]
    )

    def fechar_detalhes(e):
        dialogo_detalhes.open = False
        page.update()

    def abrir_detalhes(c_id, nome_c, nome_r, wpp, senha, sala, status):
        botoes_acao = [ft.TextButton("FECHAR", on_click=lambda e: fechar_detalhes(e))]
        
        if status == 'Não':
            botoes_acao.insert(0, ft.ElevatedButton("Entregar criança", on_click=lambda e: abrir_pergunta_entrega(c_id)))

        dialogo_detalhes.actions = botoes_acao
        dialogo_detalhes.content = ft.Column([
            ft.Text(f"#{c_id} - {nome_c}", weight="bold", size=18),
            ft.Text(f"Sala: {sala}"),
            ft.Text(f"Responsável: {nome_r}"),
            ft.Text(f"WhatsApp: {wpp}"),
            ft.Text(f"Senha de Retirada: {senha}", color="blue", weight="bold"),
            ft.Divider(),
            ft.Text(f"Status Entregue: {status}", weight="bold", color="green" if status == 'Sim' else "red")
        ], tight=True)
        
        dialogo_detalhes.open = True
        page.update()

    # ==========================================
    # TELA DE LISTAGEM E PESQUISA
    # ==========================================
    container_lista = ft.Column(horizontal_alignment="center", spacing=10)

    def carregar_listagem(termo_busca=""):
        container_lista.controls.clear()
        
        conn = sqlite3.connect("refukids.db")
        cursor = conn.cursor()
        
        if termo_busca:
            cursor.execute('''
                SELECT id, nome_crianca, nome_responsavel, whatsapp, senha, sala, status_entregue 
                FROM criancas 
                WHERE nome_crianca LIKE ? OR nome_responsavel LIKE ?
            ''', (f'%{termo_busca}%', f'%{termo_busca}%'))
        else:
            cursor.execute('SELECT id, nome_crianca, nome_responsavel, whatsapp, senha, sala, status_entregue FROM criancas')
            
        registros = cursor.fetchall()
        conn.close()

        if not registros:
            container_lista.controls.append(ft.Text("Nenhuma criança encontrada.", color="grey"))
        else:
            for reg in registros:
                c_id, nome_c, nome_r, wpp, senha, sala, status = reg
                
                cor_status = "green" if status == 'Sim' else "orange"
                
                card = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(f"#{c_id} - {nome_c}", weight="bold", size=16),
                            ft.Text(f"[{sala}]", size=12, color="grey")
                        ], alignment="spaceBetween"),
                        ft.Text(f"Responsável: {nome_r}"),
                        ft.Row([
                            ft.Text(f"Senha: {senha}", color="blue", weight="bold"),
                            ft.Text(f"Entregue: {status}", color=cor_status, weight="bold")
                        ], alignment="spaceBetween")
                    ]),
                    padding=15,
                    width=300,
                    border_radius=8,
                    bgcolor="white24",
                    on_click=lambda e, cid=c_id, nc=nome_c, nr=nome_r, wp=wpp, sn=senha, sl=sala, st=status: abrir_detalhes(cid, nc, nr, wp, sn, sl, st)
                )
                container_lista.controls.append(card)
        page.update()

    campo_pesquisa = ft.TextField(
        label="Pesquisar por nome...",
        width=300,
        border_radius=8,
        on_change=lambda e: carregar_listagem(e.control.value)
    )

    # ==========================================
    # LÓGICA DO BOTÃO SALVAR
    # ==========================================
    dialogo_sucesso = ft.AlertDialog(
        title=ft.Text("Sucesso"),
        content=ft.Text(""), 
        actions=[ft.TextButton("NÃO COMPARTILHAR", on_click=lambda e: fechar_alerta(e))]
    )

    def fechar_alerta(e):
        dialogo_sucesso.open = False
        page.update()

    def salvar_dados(e):
        sala = escala_sala[0]
        nome_c = campo_nome_crianca.value
        nome_r = campo_nome_responsavel.value
        wpp = campo_wpp_responsavel.value
        foto = caminho_foto_atual[0]
        
        if sala == "Nenhuma sala selecionada":
            dialogo_sucesso.title = ft.Text("Atenção")
            dialogo_sucesso.content = ft.Text("Por favor, selecione uma sala no botão 'Salas' no topo antes de salvar!")
            dialogo_sucesso.open = True
            page.update()
            return

        if not nome_c:
            return

        senha = str(random.randint(1000, 9999))
        
        conn = sqlite3.connect("refukids.db")
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO criancas (nome_crianca, nome_responsavel, whatsapp, senha, foto_entrada, sala) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (nome_c, nome_r, wpp, senha, foto, sala))
        
        numero_crianca = cursor.lastrowid 
        conn.commit()
        conn.close()
        
        dialogo_sucesso.title = ft.Text("Sucesso")
        dialogo_sucesso.content = ft.Text(f"Criança nº {numero_crianca} cadastrada com sucesso com senha: {senha}")
        dialogo_sucesso.open = True
        
        campo_nome_crianca.value = ""
        campo_nome_responsavel.value = ""
        campo_wpp_responsavel.value = ""
        caminho_foto_atual[0] = None
        btn_foto.content = ft.Text("Tirar foto da entrada")
        btn_foto.bgcolor = None
        btn_foto.color = None
        
        carregar_listagem()
        page.update()

    # Registra todos os diálogos no overlay
    page.overlay.append(dialogo_sucesso)
    page.overlay.append(dialogo_detalhes)
    page.overlay.append(dialogo_entrega)
    page.overlay.append(dialogo_salas)
    page.overlay.append(dialogo_confirmar_encerramento)

    # ==========================================
    # CABEÇALHO COM O BOTÃO DE SALAS
    # ==========================================
    cabecalho = ft.Row(
        alignment="spaceBetween",
        width=300,
        controls=[
            ft.Text("Refúkids", weight="bold", size=18),
            ft.OutlinedButton(
                content=texto_botao_sala,
                on_click=lambda e: setattr(dialogo_salas, 'open', True) or page.update()
            )
        ]
    )

    # ==========================================
    # TELAS VISUAIS
    # ==========================================
    tela_adicionar = ft.Column(
        horizontal_alignment="center",
        visible=True,
        controls=[
            ft.Container(height=10),
            cabecalho,
            ft.Container(height=15),
            ft.Text("Adicionar Criança", size=22, weight="bold"),
            ft.Container(height=15),
            btn_foto, 
            ft.Container(height=15),
            campo_nome_crianca,
            campo_nome_responsavel,
            campo_wpp_responsavel,
            ft.Container(height=15),
            ft.ElevatedButton(content=ft.Text("Salvar"), width=300, height=50, on_click=salvar_dados),
        ]
    )

    tela_listagem = ft.Column(
        horizontal_alignment="center",
        visible=False,
        controls=[
            ft.Container(height=10),
            cabecalho,
            ft.Container(height=15),
            ft.Text("Crianças na Sala", size=22, weight="bold"),
            ft.Container(height=10),
            campo_pesquisa,
            ft.Container(height=15),
            container_lista,
        ]
    )

    # ==========================================
    # NAVEGAÇÃO
    # ==========================================
    def navegar(e, destino):
        if destino == "listagem":
            carregar_listagem()
            tela_listagem.visible = True
            tela_adicionar.visible = False
        else:
            tela_listagem.visible = False
            tela_adicionar.visible = True
        page.update()

    menu_botoes = ft.Row(
        alignment="center",
        controls=[
            ft.ElevatedButton(content=ft.Text("Listagem"), on_click=lambda e: navegar(e, "listagem")),
            ft.ElevatedButton(content=ft.Text("Adicionar"), on_click=lambda e: navegar(e, "adicionar")),
        ]
    )

    carregar_listagem()
    page.add(menu_botoes, tela_adicionar, tela_listagem)

ft.app(target=main)