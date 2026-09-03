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

    page.title = "Refúkids"
    page.theme_mode = ft.ThemeMode.DARK
    page.horizontal_alignment = "center"
    page.scroll = "auto"
    
    # Variáveis de Estado
    escala_sala = ["Nenhuma"]
    sala_travada = [False]
    caminho_foto_atual = [None]
    crianca_selecionada_id = [None]
    modo_foto_saida = [False]

    # ==========================================
    # CÂMERA REAL DO CELULAR (FILE PICKER)
    # ==========================================
    def foto_selecionada(e: ft.FilePickerResultEvent):
        if e.files and len(e.files) > 0:
            caminho_obtido = e.files[0].path
            if modo_foto_saida[0]:
                finalizar_entrega_com_foto(caminho_obtido)
            else:
                caminho_foto_atual[0] = caminho_obtido
                btn_foto.content = ft.Text("Foto OK ✔️")
                btn_foto.bgcolor = "green"
                btn_foto.color = "white"
                page.update()

    seletor_camera = ft.FilePicker(on_result=foto_selecionada)
    page.overlay.append(seletor_camera)

    def acionar_camera_entrada(e):
        modo_foto_saida[0] = False
        seletor_camera.pick_files(
            allow_multiple=False,
            file_type=ft.FilePickerFileType.IMAGE
        )

    # ==========================================
    # BOTÃO E DIÁLOGOS DE SALAS
    # ==========================================
    texto_botao_sala = ft.Text("Salas: Nenhuma", size=12, weight="bold")

    def mudar_sala(nova_sala):
        escala_sala[0] = nova_sala
        texto_botao_sala.value = f"Sala: {nova_sala}"
        dialogo_salas.open = False
        page.update()

    def executar_encerramento():
        sala_atual = escala_sala[0]
        if sala_atual != "Nenhuma":
            conn = sqlite3.connect("refukids.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM criancas WHERE sala = ?", (sala_atual,))
            conn.commit()
            conn.close()

        dialogo_confirmar_encerramento.open = False
        dialogo_salas.open = False
        escala_sala[0] = "Nenhuma"
        sala_travada[0] = False
        texto_botao_sala.value = "Salas: Nenhuma"
        carregar_listagem()
        page.update()

    dialogo_confirmar_encerramento = ft.AlertDialog(
        title=ft.Text("⚠️ Encerrar Sala"),
        content=ft.Text("Tem certeza que deseja apagar todos os registros desta sala? Ação irreversível."),
        actions=[
            ft.TextButton("CANCELAR", on_click=lambda e: setattr(dialogo_confirmar_encerramento, 'open', False) or page.update()),
            ft.ElevatedButton("SIM, APAGAR", bgcolor="red", color="white", on_click=lambda e: executar_encerramento()),
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
            ft.TextButton(
                "Encerrar sala", 
                on_click=lambda e: setattr(dialogo_confirmar_encerramento, 'open', True) or page.update(), 
                style=ft.ButtonStyle(color="red")
            ),
        ], tight=True),
        actions=[ft.TextButton("Cancelar", on_click=lambda e: setattr(dialogo_salas, 'open', False) or page.update())]
    )

    def tentar_abrir_menu_salas(e):
        if sala_travada[0]:
            dialogo_sucesso.title = ft.Text("Sala Bloqueada")
            dialogo_sucesso.content = ft.Text("A sala já está em andamento. Para trocar, é necessário 'Encerrar sala'.")
            dialogo_sucesso.open = True
            page.update()
        else:
            dialogo_salas.open = True
            page.update()

    # ==========================================
    # BARRA SUPERIOR NATIVA (APPBAR - NÃO COLA NO NOTCH)
    # ==========================================
    page.app_bar = ft.AppBar(
        leading=ft.Icon(ft.Icons.CHILD_CARE),
        leading_width=40,
        title=ft.Text("Refúkids", weight="bold"),
        center_title=False,
        actions=[
            ft.Container(
                content=ft.OutlinedButton(
                    content=texto_botao_sala,
                    on_click=tentar_abrir_menu_salas
                ),
                padding=ft.padding.only(right=15)
            )
        ]
    )

    # ==========================================
    # CAMPOS DO FORMULÁRIO (ADICIONAR)
    # ==========================================
    campo_nome_crianca = ft.TextField(label="Nome da criança", width=320, border_radius=8)
    campo_nome_responsavel = ft.TextField(label="Nome do responsável", width=320, border_radius=8)
    campo_wpp_responsavel = ft.TextField(label="Wpp do responsável", width=320, border_radius=8, keyboard_type="phone")

    btn_foto = ft.ElevatedButton(
        content=ft.Text("Tirar foto da entrada"), 
        width=320, 
        height=50,
        on_click=acionar_camera_entrada
    )

    # ==========================================
    # DIÁLOGOS DE ENTREGA E DETALHES
    # ==========================================
    def finalizar_entrega_com_foto(caminho_foto):
        c_id = crianca_selecionada_id[0]
        conn = sqlite3.connect("refukids.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE criancas SET status_entregue = 'Sim', foto_saida = ? WHERE id = ?", (caminho_foto, c_id))
        conn.commit()
        conn.close()
        carregar_listagem(campo_pesquisa.value)
        page.update()

    def confirmar_entrega_sem_foto():
        finalizar_entrega_com_foto(None)
        dialogo_entrega.open = False
        page.update()

    def confirmar_entrega_com_camera():
        dialogo_entrega.open = False
        page.update()
        modo_foto_saida[0] = True
        seletor_camera.pick_files(allow_multiple=False, file_type=ft.FilePickerFileType.IMAGE)

    dialogo_entrega = ft.AlertDialog(
        title=ft.Text("Entregar criança"),
        content=ft.Text("Deseja bater uma foto do responsável que buscou?"),
        actions=[
            ft.TextButton("NÃO", on_click=lambda e: confirmar_entrega_sem_foto()),
            ft.TextButton("SIM", on_click=lambda e: confirmar_entrega_com_camera()),
        ]
    )

    dialogo_detalhes = ft.AlertDialog(
        title=ft.Text("Detalhes da Criança"),
        content=ft.Column([], tight=True),
        actions=[ft.TextButton("FECHAR", on_click=lambda e: setattr(dialogo_detalhes, 'open', False) or page.update())]
    )

    def abrir_detalhes(c_id, nome_c, nome_r, wpp, senha, sala, status):
        crianca_selecionada_id[0] = c_id
        botoes = [ft.TextButton("FECHAR", on_click=lambda e: setattr(dialogo_detalhes, 'open', False) or page.update())]
        
        if status == 'Não':
            botoes.insert(0, ft.ElevatedButton("Entregar criança", on_click=lambda e: setattr(dialogo_detalhes, 'open', False) or setattr(dialogo_entrega, 'open', True) or page.update()))

        dialogo_detalhes.actions = botoes
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
            container_lista.controls.append(ft.Text("Nenhuma criança listada", color="grey"))
        else:
            for reg in registros:
                c_id, nome_c, nome_r, wpp, senha, sala, status = reg
                card = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(f"#{c_id} - {nome_c}", weight="bold", size=16),
                            ft.Text(f"[{sala}]", size=12, color="grey")
                        ], alignment="spaceBetween"),
                        ft.Text(f"Responsável: {nome_r}"),
                        ft.Row([
                            ft.Text(f"Senha: {senha}", color="blue", weight="bold"),
                            ft.Text(f"Entregue: {status}", color="green" if status == 'Sim' else "orange", weight="bold")
                        ], alignment="spaceBetween")
                    ]),
                    padding=15,
                    width=320,
                    border_radius=8,
                    bgcolor="white24",
                    on_click=lambda e, cid=c_id, nc=nome_c, nr=nome_r, wp=wpp, sn=senha, sl=sala, st=status: abrir_detalhes(cid, nc, nr, wp, sn, sl, st)
                )
                container_lista.controls.append(card)
        page.update()

    campo_pesquisa = ft.TextField(
        label="Pesquisar por nome...",
        width=320,
        border_radius=8,
        on_change=lambda e: carregar_listagem(e.control.value)
    )

    # ==========================================
    # SALVAMENTO E FEEDBACK
    # ==========================================
    dialogo_sucesso = ft.AlertDialog(
        title=ft.Text("Sucesso"),
        content=ft.Text(""), 
        actions=[ft.TextButton("FECHAR", on_click=lambda e: setattr(dialogo_sucesso, 'open', False) or page.update())]
    )

    def salvar_dados(e):
        sala = escala_sala[0]
        nome_c = campo_nome_crianca.value
        nome_r = campo_nome_responsavel.value
        wpp = campo_wpp_responsavel.value
        foto = caminho_foto_atual[0]
        
        if sala == "Nenhuma":
            dialogo_sucesso.title = ft.Text("Atenção")
            dialogo_sucesso.content = ft.Text("Selecione uma sala no canto superior antes de cadastrar!")
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
        
        # Trava a sala após o primeiro cadastro do turno
        sala_travada[0] = True
        
        dialogo_sucesso.title = ft.Text("Sucesso")
        dialogo_sucesso.content = ft.Text(f"Criança nº {numero_crianca} cadastrada com sucesso! Senha: {senha}")
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

    # Registra diálogos
    page.overlay.extend([dialogo_sucesso, dialogo_detalhes, dialogo_entrega, dialogo_salas, dialogo_confirmar_encerramento])

    # ==========================================
    # CORPO DAS TELAS
    # ==========================================
    tela_adicionar = ft.Column(
        horizontal_alignment="center",
        visible=True,
        controls=[
            ft.Container(height=10),
            ft.Text("Adicionar Criança", size=22, weight="bold"),
            ft.Container(height=10),
            btn_foto, 
            ft.Container(height=10),
            campo_nome_crianca,
            campo_nome_responsavel,
            campo_wpp_responsavel,
            ft.Container(height=15),
            ft.ElevatedButton(content=ft.Text("Salvar"), width=320, height=50, on_click=salvar_dados),
        ]
    )

    tela_listagem = ft.Column(
        horizontal_alignment="center",
        visible=False,
        controls=[
            ft.Container(height=10),
            campo_pesquisa,
            ft.Container(height=10),
            container_lista,
        ]
    )

    # ==========================================
    # BARRA DE NAVEGAÇÃO INFERIOR (ESTILO APP ANTIGO)
    # ==========================================
    def mudar_aba(e):
        idx = e.control.selected_index
        if idx == 0:
            carregar_listagem()
            tela_listagem.visible = True
            tela_adicionar.visible = False
        else:
            tela_listagem.visible = False
            tela_adicionar.visible = True
        page.update()

    page.navigation_bar = ft.NavigationBar(
        selected_index=1,
        on_change=mudar_aba,
        destinations=[
            ft.NavigationDestination(icon=ft.Icons.GRID_VIEW, label="Listagem"),
            ft.NavigationDestination(icon=ft.Icons.EDIT_OUTLINED, label="Adicionar"),
        ]
    )

    carregar_listagem()
    page.add(tela_adicionar, tela_listagem)

ft.app(target=main)
