import flet as ft
import sqlite3
import random
import urllib.parse

# ==========================================
# BANCO DE DADOS E SALVAMENTO AUTOMÁTICO
# ==========================================
def inicializar_banco():
    conn = sqlite3.connect("refukids.db")
    cursor = conn.cursor()
    # Tabela de Crianças
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
    # Tabela de Configurações (Guarda onde você parou)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS configuracoes (
            chave TEXT PRIMARY KEY,
            valor TEXT
        )
    ''')
    # Correções automáticas caso o banco seja antigo
    try: cursor.execute("ALTER TABLE criancas ADD COLUMN sala TEXT")
    except: pass
    try: cursor.execute("ALTER TABLE criancas ADD COLUMN status_entregue TEXT DEFAULT 'Não'")
    except: pass
    try: cursor.execute("ALTER TABLE criancas ADD COLUMN foto_saida TEXT")
    except: pass
    
    conn.commit()
    conn.close()

def obter_configuracao(chave, padrao=""):
    try:
        conn = sqlite3.connect("refukids.db")
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM configuracoes WHERE chave = ?", (chave,))
        resultado = cursor.fetchone()
        conn.close()
        return resultado[0] if resultado else padrao
    except:
        return padrao

def salvar_configuracao(chave, valor):
    conn = sqlite3.connect("refukids.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES (?, ?)", (chave, valor))
    conn.commit()
    conn.close()

def main(page: ft.Page):
    inicializar_banco()
    page.theme_mode = ft.ThemeMode.LIGHT
    
    # Restaura exatamente onde o usuário parou na última vez
    escala_sala = [obter_configuracao("sala_atual", "Refubabies")]
    aba_atual = [int(obter_configuracao("aba_atual", "0"))]
    
    caminho_foto_atual = [None]
    crianca_ativa = [None]
    dados_ultimo_cadastro = {}
    modo_foto_saida = [False]

    def verificar_sala_em_andamento():
        conn = sqlite3.connect("refukids.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM criancas WHERE sala = ?", (escala_sala[0],))
        total = cursor.fetchone()[0]
        conn.close()
        return total > 0

    def limpar_numero(telefone):
        digitos = ''.join(filter(str.isdigit, str(telefone)))
        if len(digitos) in [10, 11] and not digitos.startswith("55"):
            return f"55{digitos}"
        return digitos

    # ==========================================
    # CÂMERA DO APARELHO
    # ==========================================
    def foto_selecionada(e: ft.FilePickerResultEvent):
        if e.files and len(e.files) > 0:
            caminho_obtido = e.files[0].path
            if modo_foto_saida[0]:
                finalizar_entrega(caminho_obtido)
            else:
                caminho_foto_atual[0] = caminho_obtido
                btn_foto.content = ft.Text("Foto OK ✔️", color="white")
                btn_foto.bgcolor = "green"
                page.update()

    seletor_camera = ft.FilePicker(on_result=foto_selecionada)
    page.overlay.append(seletor_camera)

    def abrir_camera_entrada(e):
        modo_foto_saida[0] = False
        seletor_camera.pick_files(allow_multiple=False, file_type=ft.FilePickerFileType.IMAGE)

    # ==========================================
    # UTILITÁRIOS PARA DIÁLOGOS
    # ==========================================
    def fechar_dialogo(dlg):
        dlg.open = False
        page.update()

    def abrir_dialogo(dlg):
        dlg.open = True
        page.update()

    # ==========================================
    # MENU DE SALAS (Totalmente Desbloqueado)
    # ==========================================
    texto_botao_sala = ft.Text(f"👥 {escala_sala[0]}", size=12, weight="bold")

    dialogo_bloqueio = ft.AlertDialog(
        title=ft.Text("Sala em Andamento"),
        content=ft.Text("Esta sala possui crianças. Para iniciar uma sala diferente, clique primeiro em 'Encerrar sala' no menu."),
        actions=[ft.TextButton("OK", on_click=lambda e: fechar_dialogo(dialogo_bloqueio))]
    )

    def tentar_mudar_sala(nova_sala):
        if nova_sala == escala_sala[0]:
            fechar_dialogo(dialogo_salas)
            return

        if verificar_sala_em_andamento():
            fechar_dialogo(dialogo_salas)
            abrir_dialogo(dialogo_bloqueio)
            return

        # Troca de sala permitida
        escala_sala[0] = nova_sala
        salvar_configuracao("sala_atual", nova_sala)
        texto_botao_sala.value = f"👥 {nova_sala}"
        fechar_dialogo(dialogo_salas)
        carregar_listagem()
        page.update()

    def executar_encerramento(e):
        sala_atual = escala_sala[0]
        conn = sqlite3.connect("refukids.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM criancas WHERE sala = ?", (sala_atual,))
        conn.commit()
        conn.close()

        fechar_dialogo(dialogo_confirmar_encerramento)
        carregar_listagem()

    dialogo_confirmar_encerramento = ft.AlertDialog(
        title=ft.Text("⚠️ Encerrar Sala"),
        content=ft.Text("Tem certeza que deseja apagar todos os registros desta sala? Esta ação é irreversível."),
        actions=[
            ft.TextButton("CANCELAR", on_click=lambda e: fechar_dialogo(dialogo_confirmar_encerramento)),
            ft.ElevatedButton("SIM, APAGAR", bgcolor="red", color="white", on_click=executar_encerramento),
        ]
    )

    def preparar_encerramento(e):
        fechar_dialogo(dialogo_salas)
        abrir_dialogo(dialogo_confirmar_encerramento)

    # O menu sempre abre, independente se a sala tem criança ou não
    dialogo_salas = ft.AlertDialog(
        title=ft.Text("Escolha a Sala"),
        content=ft.Column([
            ft.TextButton("Refubabies", on_click=lambda e: tentar_mudar_sala("Refubabies")),
            ft.TextButton("Refukids 1", on_click=lambda e: tentar_mudar_sala("Refukids 1")),
            ft.TextButton("Refukids 2", on_click=lambda e: tentar_mudar_sala("Refukids 2")),
            ft.TextButton("Refuteens", on_click=lambda e: tentar_mudar_sala("Refuteens")),
            ft.Divider(),
            ft.TextButton("Encerrar sala", on_click=preparar_encerramento, style=ft.ButtonStyle(color="red")),
        ], tight=True),
        actions=[ft.TextButton("Cancelar", on_click=lambda e: fechar_dialogo(dialogo_salas))]
    )

    botao_acao_sala = ft.Container(
        content=ft.OutlinedButton(
            content=texto_botao_sala,
            on_click=lambda e: abrir_dialogo(dialogo_salas)
        ),
        padding=ft.padding.only(right=15)
    )

    # ==========================================
    # CABEÇALHO COM LOGO OFICIAL
    # ==========================================
    icone_logo = ft.Container(
        content=ft.Image(src="logo.png", width=40, height=40, fit=ft.ImageFit.CONTAIN),
        padding=ft.padding.only(left=8),
        alignment=ft.alignment.center
    )

    # ==========================================
    # FORMULÁRIO DE CADASTRO
    # ==========================================
    btn_foto = ft.OutlinedButton(
        content=ft.Text("Tirar foto", color="black"), 
        width=320, 
        height=45,
        on_click=abrir_camera_entrada
    )
    campo_nome_crianca = ft.TextField(label="Nome da criança", width=320, border_radius=6)
    campo_nome_responsavel = ft.TextField(label="Nome do responsável", width=320, border_radius=6)
    campo_wpp_responsavel = ft.TextField(label="Wpp do responsável", width=320, border_radius=6, keyboard_type="phone")

    def fechar_e_limpar_formulario(e=None):
        fechar_dialogo(dialogo_sucesso)
        campo_nome_crianca.value = ""
        campo_nome_responsavel.value = ""
        campo_wpp_responsavel.value = ""
        caminho_foto_atual[0] = None
        btn_foto.content = ft.Text("Tirar foto", color="black")
        btn_foto.bgcolor = None
        carregar_listagem()

    def compartilhar_whatsapp(e=None):
        dados = dados_ultimo_cadastro
        msg = (
            f"Ola {dados.get('responsavel', '')}\n"
            f"Aqui é o tio(a) da Refukids, estamos muito felizes de ter sua criança cultuando aqui conosco.\n\n"
            f"Sala: {dados.get('sala', '')}\n"
            f"Nome: {dados.get('crianca', '')}\n"
            f"Número: {dados.get('id', '')}\n"
            f"Senha: {dados.get('senha', '')}\n\n"
            f"Lembramos que é importante que ao final do culto Você venha buscar sua criança aqui na sala, e não terceiros.\n\n"
            f"Deus abençoe seu culto."
        )
        numero = limpar_numero(dados.get('whatsapp', ''))
        texto_url = urllib.parse.quote(msg)
        page.launch_url(f"https://wa.me/{numero}?text={texto_url}")
        fechar_e_limpar_formulario()

    dialogo_sucesso = ft.AlertDialog(
        title=ft.Text("Sucesso", weight="bold"),
        content=ft.Text(""),
        actions=[
            ft.TextButton("NÃO", on_click=fechar_e_limpar_formulario),
            ft.TextButton("COMPARTILHAR", on_click=compartilhar_whatsapp),
        ]
    )

    def salvar_dados(e):
        sala = escala_sala[0]
        nome_c = campo_nome_crianca.value
        nome_r = campo_nome_responsavel.value
        wpp = campo_wpp_responsavel.value
        foto = caminho_foto_atual[0]
        
        if not nome_c or not nome_r:
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
        
        salvar_configuracao("sala_atual", sala)
        
        dados_ultimo_cadastro.clear()
        dados_ultimo_cadastro.update({
            "id": numero_crianca, "crianca": nome_c, "responsavel": nome_r,
            "whatsapp": wpp, "senha": senha, "sala": sala
        })

        dialogo_sucesso.content = ft.Text(f"Criança nº {numero_crianca} cadastrada com sucesso\ncom senha: {senha}")
        abrir_dialogo(dialogo_sucesso)

    # ==========================================
    # TELA DE DETALHES & ENTREGA
    # ==========================================
    imagem_detalhe = ft.Image(width=340, height=220, fit=ft.ImageFit.COVER, border_radius=8)
    txt_detalhe_numero = ft.Text("", size=16, weight="bold")
    txt_detalhe_senha = ft.Text("", size=16, weight="bold")
    txt_detalhe_nome = ft.Text("", size=16, weight="bold")
    txt_detalhe_resp = ft.Text("", size=16, weight="bold")
    txt_detalhe_status = ft.Text("", size=16, weight="bold")

    def finalizar_entrega(foto_saida=None):
        c = crianca_ativa[0]
        if not c: return
        conn = sqlite3.connect("refukids.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE criancas SET status_entregue = 'Sim', foto_saida = ? WHERE id = ?", (foto_saida, c['id']))
        conn.commit()
        conn.close()

        fechar_dialogo(dialogo_entrega)
        c['status'] = 'Sim'
        txt_detalhe_status.value = "Sim"
        btn_entregar.visible = False
        carregar_listagem()

    def confirmar_entrega_com_foto(e):
        fechar_dialogo(dialogo_entrega)
        modo_foto_saida[0] = True
        seletor_camera.pick_files(allow_multiple=False, file_type=ft.FilePickerFileType.IMAGE)

    dialogo_entrega = ft.AlertDialog(
        title=ft.Text("Entregar criança"),
        content=ft.Text("Deseja bater uma foto do responsável que buscou?"),
        actions=[
            ft.TextButton("NÃO", on_click=lambda e: finalizar_entrega(None)),
            ft.TextButton("SIM", on_click=confirmar_entrega_com_foto),
        ]
    )

    btn_entregar = ft.OutlinedButton(
        content=ft.Row([ft.Icon(ft.Icons.HANDSHAKE_OUTLINED, color="black"), ft.Text("Entregar criança", color="black")], alignment="center"),
        width=340, height=45,
        on_click=lambda e: abrir_dialogo(dialogo_entrega)
    )

    btn_ligar = ft.OutlinedButton(
        content=ft.Row([ft.Icon(ft.Icons.PHONE, color="black"), ft.Text("Ligar para o Responsável", color="black")], alignment="center"),
        width=340, height=45,
        on_click=lambda e: page.launch_url(f"tel:{limpar_numero(crianca_ativa[0]['whatsapp'])}")
    )

    btn_wpp = ft.OutlinedButton(
        content=ft.Row([ft.Icon(ft.Icons.CHAT_OUTLINED, color="black"), ft.Text("Whatsapp do Responsável", color="black")], alignment="center"),
        width=340, height=45,
        on_click=lambda e: page.launch_url(f"https://wa.me/{limpar_numero(crianca_ativa[0]['whatsapp'])}")
    )

    def abrir_tela_detalhes(c_id, nome, resp, wpp, senha, sala, foto, status):
        crianca_ativa[0] = {
            "id": c_id, "nome": nome, "responsavel": resp, 
            "whatsapp": wpp, "senha": senha, "sala": sala, "status": status
        }
        txt_detalhe_numero.value = str(c_id)
        txt_detalhe_senha.value = str(senha)
        txt_detalhe_nome.value = nome
        txt_detalhe_resp.value = resp
        txt_detalhe_status.value = status
        
        if foto:
            imagem_detalhe.src = foto
            imagem_detalhe.visible = True
        else:
            imagem_detalhe.visible = False

        btn_entregar.visible = (status == "Não")
        page.go("/detalhes")

    # ==========================================
    # TELA DE LISTAGEM COM PESQUISA RESTAURADA
    # ==========================================
    grid_criancas = ft.GridView(
        expand=True, runs_count=2, max_extent=170,
        child_aspect_ratio=1.0, spacing=8, run_spacing=8,
    )

    txt_sem_criancas = ft.Text("Nenhuma criança listada", color="grey", size=14, visible=False)

    def carregar_listagem(termo=""):
        grid_criancas.controls.clear()
        sala_atual = escala_sala[0]
        
        conn = sqlite3.connect("refukids.db")
        cursor = conn.cursor()
        if termo:
            cursor.execute('SELECT id, nome_crianca, nome_responsavel, whatsapp, senha, sala, foto_entrada, status_entregue FROM criancas WHERE sala = ? AND (nome_crianca LIKE ? OR nome_responsavel LIKE ?)', (sala_atual, f'%{termo}%', f'%{termo}%'))
        else:
            cursor.execute('SELECT id, nome_crianca, nome_responsavel, whatsapp, senha, sala, foto_entrada, status_entregue FROM criancas WHERE sala = ?', (sala_atual,))
        
        registros = cursor.fetchall()
        conn.close()

        if not registros:
            txt_sem_criancas.visible = True
        else:
            txt_sem_criancas.visible = False
            for reg in registros:
                c_id, nome_c, nome_r, wpp, senha, sala, foto, status = reg
                card_conteudo = ft.Stack([
                    ft.Image(
                        src=foto if foto else "https://via.placeholder.com/150",
                        fit=ft.ImageFit.COVER, width=170, height=170, border_radius=8
                    ),
                    ft.Container(
                        content=ft.Text(str(c_id), weight="bold", color="black", size=13),
                        width=28, height=28, bgcolor="white", border_radius=14,
                        alignment=ft.alignment.center, right=8, bottom=8,
                    )
                ])

                card = ft.Container(
                    content=card_conteudo,
                    on_click=lambda e, cid=c_id, nc=nome_c, nr=nome_r, wp=wpp, sn=senha, sl=sala, ft_p=foto, st=status: abrir_tela_detalhes(cid, nc, nr, wp, sn, sl, ft_p, st)
                )
                grid_criancas.controls.append(card)
        page.update()

    campo_pesquisa = ft.TextField(
        label="Pesquisar por nome...",
        width=320, height=45, border_radius=6,
        prefix_icon=ft.Icons.SEARCH,
        on_change=lambda e: carregar_listagem(e.control.value)
    )

    page.overlay.extend([
        dialogo_bloqueio, dialogo_confirmar_encerramento, 
        dialogo_salas, dialogo_sucesso, dialogo_entrega
    ])

    # ==========================================
    # CONTEÚDOS DAS ABAS
    # ==========================================
    tela_adicionar = ft.Column(
        horizontal_alignment="center", scroll="auto",
        controls=[
            ft.Container(height=15),
            btn_foto, ft.Divider(height=20, color="transparent"),
            campo_nome_crianca, campo_nome_responsavel, campo_wpp_responsavel,
            ft.Container(height=25),
            ft.OutlinedButton(content=ft.Text("Salvar", color="black"), width=320, height=45, on_click=salvar_dados),
        ]
    )

    tela_listagem = ft.Column(
        horizontal_alignment="center", expand=True,
        controls=[
            ft.Container(height=10),
            campo_pesquisa,
            ft.Container(height=5),
            txt_sem_criancas,
            grid_criancas,
        ]
    )

    tela_detalhes_conteudo = ft.Column(
        horizontal_alignment="center", scroll="auto",
        controls=[
            ft.Container(height=5),
            imagem_detalhe,
            ft.Container(height=10),
            ft.Container(
                width=340,
                content=ft.Column([
                    ft.Text("Número:", color="grey", size=13), txt_detalhe_numero,
                    ft.Text("Senha:", color="grey", size=13), txt_detalhe_senha,
                    ft.Text("Nome:", color="grey", size=13), txt_detalhe_nome,
                    ft.Text("Responsável:", color="grey", size=13), txt_detalhe_resp,
                    ft.Text("Entregue:", color="grey", size=13), txt_detalhe_status,
                ], spacing=4)
            ),
            ft.Container(height=15),
            btn_entregar, btn_ligar, btn_wpp,
            ft.Container(height=25),
        ]
    )

    # ==========================================
    # SISTEMA DE ROTAS E BOTÃO VOLTAR
    # ==========================================
    def mudar_aba(e):
        idx = e.control.selected_index
        aba_atual[0] = idx
        salvar_configuracao("aba_atual", str(idx))
        page.go("/")

    def route_change(e):
        page.views.clear()
        
        # Constrói a tela principal com base na aba salva
        nav_bar = ft.NavigationBar(
            selected_index=aba_atual[0],
            on_change=mudar_aba,
            bgcolor="white",
            destinations=[
                ft.NavigationDestination(icon=ft.Icons.GRID_VIEW, label="Listagem"),
                ft.NavigationDestination(icon=ft.Icons.EDIT_OUTLINED, label="Adicionar"),
            ]
        )
        
        appbar_principal = ft.AppBar(
            leading=icone_logo,
            leading_width=60,
            title=ft.Text("Listagem" if aba_atual[0] == 0 else "Adicionar", weight="bold"),
            center_title=False,
            actions=[botao_acao_sala],
            bgcolor="white"
        )
        
        page.views.append(ft.View(
            route="/",
            controls=[tela_listagem if aba_atual[0] == 0 else tela_adicionar],
            appbar=appbar_principal,
            navigation_bar=nav_bar,
            horizontal_alignment="center"
        ))

        # Se estiver na tela de Detalhes, adiciona na frente
        if page.route == "/detalhes":
            appbar_detalhes = ft.AppBar(
                leading=ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: page.go("/")),
                leading_width=40,
                title=ft.Text(crianca_ativa[0]["nome"] if crianca_ativa[0] else "", weight="bold"),
                bgcolor="white"
            )
            page.views.append(ft.View(
                route="/detalhes",
                controls=[tela_detalhes_conteudo],
                appbar=appbar_detalhes,
                horizontal_alignment="center"
            ))
            
        page.update()

    def view_pop(e):
        # A Mágica do botão Voltar: Ao arrastar a tela nos Detalhes, volta para Listagem
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    
    carregar_listagem()
    page.go("/")

# Pasta assets obrigatória para a logo aparecer
ft.app(target=main, assets_dir="assets")
