import 'dart:io';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart' as p;
import 'package:url_launcher/url_launcher.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const RefukidsApp());
}

class RefukidsApp extends StatelessWidget {
  const RefukidsApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Refúkids',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        scaffoldBackgroundColor: Colors.white,
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.red, primary: Colors.red),
        appBarTheme: const AppBarTheme(
          backgroundColor: Colors.white,
          foregroundColor: Colors.black,
          elevation: 0.5,
        ),
      ),
      home: const HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  int _currentIndex = 1; // 0: Listagem, 1: Adicionar
  String _salaAtual = 'Refubabies';
  bool _salaTravada = false;

  final TextEditingController _nomeCriancaCtrl = TextEditingController();
  final TextEditingController _nomeRespCtrl = TextEditingController();
  final TextEditingController _wppRespCtrl = TextEditingController();

  String? _fotoEntradaPath;
  List<Map<String, dynamic>> _listaCriancas = [];
  Map<String, dynamic>? _criancaSelecionada;

  Database? _db;

  @override
  void initState() {
    super.initState();
    _inicializarBanco();
  }

  Future<void> _inicializarBanco() async {
    final dbPath = await getDatabasesPath();
    final path = p.join(dbPath, 'refukids.db');

    _db = await openDatabase(
      path,
      version: 1,
      onCreate: (db, version) async {
        await db.execute('''
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
        ''');
      },
    );
    _carregarListagem();
  }

  Future<void> _carregarListagem() async {
    if (_db == null) return;
    final dados = await _db!.query(
      'criancas',
      where: 'sala = ?',
      whereArgs: [_salaAtual],
      orderBy: 'id ASC',
    );
    setState(() {
      _listaCriancas = dados;
      if (dados.isNotEmpty) {
        _salaTravada = true;
      }
    });
  }

  // CÂMERA 100% DIRETA E EXCLUSIVA
  Future<String?> _capturarFotoNativa() async {
    final picker = ImagePicker();
    final XFile? foto = await picker.pickImage(
      source: ImageSource.camera,
      imageQuality: 75,
    );
    return foto?.path;
  }

  String _formatarNumero(String telefone) {
    final digitos = telefone.replaceAll(RegExp(r'\D'), '');
    if ((digitos.length == 10 || digitos.length == 11) && !digitos.startsWith('55')) {
      return '55$digitos';
    }
    return digitos;
  }

  Future<void> _abrirWhatsApp(String telefone, String mensagem) async {
    final numFormatado = _formatarNumero(telefone);
    final uri = Uri.parse('https://wa.me/$numFormatado?text=${Uri.encodeComponent(mensagem)}');
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  Future<void> _fazerLigacao(String telefone) async {
    final numFormatado = _formatarNumero(telefone);
    final uri = Uri.parse('tel:$numFormatado');
    await launchUrl(uri);
  }

  void _dialogoSalas() {
    if (_salaTravada) {
      showDialog(
        context: context,
        builder: (_) => AlertDialog(
          title: const Text('Sala Bloqueada'),
          content: const Text('A sala já está em andamento. Para trocar, use "Encerrar sala".'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context), child: const Text('OK')),
          ],
        ),
      );
      return;
    }

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Qual sala você está?'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            for (var sala in ['Refubabies', 'Refukids 1', 'Refukids 2', 'Refuteens'])
              TextButton(
                onPressed: () {
                  setState(() => _salaAtual = sala);
                  Navigator.pop(ctx);
                  _carregarListagem();
                },
                child: Align(alignment: Alignment.centerLeft, child: Text(sala, style: const TextStyle(color: Colors.black))),
              ),
            const Divider(),
            TextButton(
              onPressed: () {
                Navigator.pop(ctx);
                _dialogoConfirmarEncerramento();
              },
              child: const Align(alignment: Alignment.centerLeft, child: Text('Encerrar sala', style: TextStyle(color: Colors.red))),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancelar')),
        ],
      ),
    );
  }

  void _dialogoConfirmarEncerramento() {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('⚠️ Encerrar Sala'),
        content: Text('Tem certeza que deseja apagar todos os registros da sala "$_salaAtual"?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('CANCELAR')),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () async {
              await _db?.delete('criancas', where: 'sala = ?', whereArgs: [_salaAtual]);
              setState(() {
                _salaTravada = false;
                _criancaSelecionada = null;
              });
              Navigator.pop(ctx);
              _carregarListagem();
            },
            child: const Text('SIM, APAGAR', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
  }

  Future<void> _salvarCrianca() async {
    final nome = _nomeCriancaCtrl.text.trim();
    final resp = _nomeRespCtrl.text.trim();
    final wpp = _wppRespCtrl.text.trim();

    if (nome.isEmpty || resp.isEmpty) return;

    final senha = (1000 + Random().nextInt(9000)).toString();

    final id = await _db!.insert('criancas', {
      'nome_crianca': nome,
      'nome_responsavel': resp,
      'whatsapp': wpp,
      'senha': senha,
      'foto_entrada': _fotoEntradaPath,
      'sala': _salaAtual,
      'status_entregue': 'Não',
    });

    setState(() => _salaTravada = true);

    if (!mounted) return;

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        title: const Text('Sucesso', style: TextStyle(fontWeight: FontWeight.bold)),
        content: Text('Crianca nº $id cadastrada com sucesso com senha: $senha'),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.pop(ctx);
              _limparFormulario();
            },
            child: const Text('NÃO', style: TextStyle(color: Colors.black)),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(ctx);
              final msg = '''Ola $resp
Aqui é o tio(a) da Refukids, estamos muito felizes de ter sua criança cultuando aqui conosco.

Sala: $_salaAtual
Nome: $nome
Número: $id
Senha: $senha

Lembramos que é importante que ao final do culto Você venha buscar sua criança aqui na sala, e não terceiros.

Deus abençoe seu culto.''';
              _abrirWhatsApp(wpp, msg);
              _limparFormulario();
            },
            child: const Text('COMPARTILHAR', style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  void _limparFormulario() {
    _nomeCriancaCtrl.clear();
    _nomeRespCtrl.clear();
    _wppRespCtrl.clear();
    setState(() => _fotoEntradaPath = null);
    _carregarListagem();
  }

  // DIÁLOGO DE ENTREGA (FOTO DE SAÍDA)
  void _dialogoEntregar() {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Entregar criança'),
        content: const Text('Deseja bater uma foto do responsável que buscou?'),
        actions: [
          TextButton(
            onPressed: () async {
              Navigator.pop(ctx);
              await _finalizarEntrega(null);
            },
            child: const Text('NÃO', style: TextStyle(color: Colors.black)),
          ),
          TextButton(
            onPressed: () async {
              Navigator.pop(ctx);
              final fotoSaida = await _capturarFotoNativa();
              await _finalizarEntrega(fotoSaida);
            },
            child: const Text('SIM', style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  Future<void> _finalizarEntrega(String? fotoSaida) async {
    final id = _criancaSelecionada!['id'];
    await _db!.update(
      'criancas',
      {'status_entregue': 'Sim', 'foto_saida': fotoSaida},
      where: 'id = ?',
      whereArgs: [id],
    );
    await _carregarListagem();
    setState(() {
      _criancaSelecionada = _listaCriancas.firstWhere((item) => item['id'] == id);
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_criancaSelecionada != null) {
      return _buildTelaDetalhes();
    }

    return Scaffold(
      appBar: AppBar(
        leading: Icon(_currentIndex == 0 ? Icons.grid_view : Icons.face, color: _currentIndex == 0 ? Colors.red : Colors.pink),
        title: Text(_currentIndex == 0 ? 'Listagem' : 'Adicionar', style: const TextStyle(fontWeight: FontWeight.bold)),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: OutlinedButton(
              style: OutlinedButton.styleFrom(
                side: const BorderSide(color: Colors.grey),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
              ),
              onPressed: _dialogoSalas,
              child: Row(
                children: [
                  const Icon(Icons.group, size: 16, color: Colors.black),
                  const SizedBox(width: 4),
                  Text(_salaAtual, style: const TextStyle(color: Colors.black, fontSize: 13, fontWeight: FontWeight.bold)),
                ],
              ),
            ),
          ),
        ],
      ),
      body: _currentIndex == 0 ? _buildAbaListagem() : _buildAbaAdicionar(),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        selectedItemColor: Colors.red,
        unselectedItemColor: Colors.grey,
        backgroundColor: Colors.white,
        onTap: (idx) => setState(() => _currentIndex = idx),
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.grid_view), label: 'Listagem'),
          BottomNavigationBarItem(icon: Icon(Icons.edit_outlined), label: 'Adicionar'),
        ],
      ),
    );
  }

  Widget _buildAbaAdicionar() {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          OutlinedButton(
            style: OutlinedButton.styleFrom(
              minimumSize: const Size.fromHeight(48),
              backgroundColor: _fotoEntradaPath != null ? Colors.green : Colors.transparent,
              side: BorderSide(color: _fotoEntradaPath != null ? Colors.green : Colors.grey.shade400),
            ),
            onPressed: () async {
              final caminho = await _capturarFotoNativa();
              if (caminho != null) setState(() => _fotoEntradaPath = caminho);
            },
            child: Text(
              _fotoEntradaPath != null ? 'Foto OK ✔️' : 'Tirar foto',
              style: TextStyle(color: _fotoEntradaPath != null ? Colors.white : Colors.black, fontWeight: FontWeight.w600),
            ),
          ),
          const SizedBox(height: 24),
          TextField(controller: _nomeCriancaCtrl, decoration: const InputDecoration(labelText: 'Nome da criança', border: OutlineInputBorder())),
          const SizedBox(height: 16),
          TextField(controller: _nomeRespCtrl, decoration: const InputDecoration(labelText: 'Nome do responsável', border: OutlineInputBorder())),
          const SizedBox(height: 16),
          TextField(controller: _wppRespCtrl, keyboardType: TextInputType.phone, decoration: const InputDecoration(labelText: 'Wpp do responsável', border: OutlineInputBorder())),
          const SizedBox(height: 28),
          OutlinedButton(
            style: OutlinedButton.styleFrom(
              minimumSize: const Size.fromHeight(48),
              side: const BorderSide(color: Colors.black87),
            ),
            onPressed: _salvarCrianca,
            child: const Text('Salvar', style: TextStyle(color: Colors.black, fontSize: 16)),
          ),
        ],
      ),
    );
  }

  Widget _buildAbaListagem() {
    if (_listaCriancas.isEmpty) {
      return const Center(child: Text('Nenhuma criança listada', style: TextStyle(color: Colors.grey, fontSize: 16)));
    }

    return GridView.builder(
      padding: const EdgeInsets.all(12),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        crossAxisSpacing: 8,
        mainAxisSpacing: 8,
      ),
      itemCount: _listaCriancas.length,
      itemBuilder: (ctx, idx) {
        final item = _listaCriancas[idx];
        final foto = item['foto_entrada'];

        return InkWell(
          onTap: () => setState(() => _criancaSelecionada = item),
          child: Stack(
            fit: StackFit.expand,
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(6),
                child: foto != null && File(foto).existsSync()
                    ? Image.file(File(foto), fit: BoxFit.cover)
                    : Container(color: Colors.grey.shade200, child: const Icon(Icons.person, size: 50, color: Colors.grey)),
              ),
              Positioned(
                bottom: 8,
                right: 8,
                child: Container(
                  width: 30,
                  height: 30,
                  decoration: const BoxDecoration(color: Colors.white, shape: BoxShape.circle),
                  alignment: Alignment.center,
                  child: Text('${item['id']}', style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.black, fontSize: 14)),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildTelaDetalhes() {
    final c = _criancaSelecionada!;
    final foto = c['foto_entrada'];
    final entregue = c['status_entregue'] == 'Sim';

    return Scaffold(
      appBar: AppBar(
        leading: IconButton(icon: const Icon(Icons.arrow_back), onPressed: () => setState(() => _criancaSelecionada = null)),
        title: Text(c['nome_crianca'] ?? '', style: const TextStyle(fontWeight: FontWeight.bold)),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (foto != null && File(foto).existsSync())
              ClipRRect(
                borderRadius: BorderRadius.circular(6),
                child: Image.file(File(foto), height: 230, fit: BoxFit.cover),
              ),
            const SizedBox(height: 16),
            _infoLinha('Número:', '${c['id']}'),
            _infoLinha('Senha:', '${c['senha']}'),
            _infoLinha('Nome:', '${c['nome_crianca']}'),
            _infoLinha('Responsável:', '${c['nome_responsavel']}'),
            _infoLinha('Entregue:', c['status_entregue'] ?? 'Não'),
            const SizedBox(height: 24),
            if (!entregue) ...[
              OutlinedButton.icon(
                style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(48), side: const BorderSide(color: Colors.black87)),
                icon: const Icon(Icons.handshake_outlined, color: Colors.black),
                label: const Text('Entregar criança', style: TextStyle(color: Colors.black)),
                onPressed: _dialogoEntregar,
              ),
              const SizedBox(height: 10),
            ],
            OutlinedButton.icon(
              style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(48), side: const BorderSide(color: Colors.black87)),
              icon: const Icon(Icons.phone, color: Colors.black),
              label: const Text('Ligar para o Responsável', style: TextStyle(color: Colors.black)),
              onPressed: () => _fazerLigacao(c['whatsapp'] ?? ''),
            ),
            const SizedBox(height: 10),
            OutlinedButton.icon(
              style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(48), side: const BorderSide(color: Colors.black87)),
              icon: const Icon(Icons.chat_bubble_outline, color: Colors.black),
              label: const Text('Whatsapp do Responsável', style: TextStyle(color: Colors.black)),
              onPressed: () => _abrirWhatsApp(c['whatsapp'] ?? '', 'Olá, precisamos falar sobre a criança ${c['nome_crianca']}.'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _infoLinha(String rotulo, String valor) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(rotulo, style: const TextStyle(color: Colors.grey, fontSize: 13)),
          Text(valor, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 17)),
        ],
      ),
    );
  }
}
