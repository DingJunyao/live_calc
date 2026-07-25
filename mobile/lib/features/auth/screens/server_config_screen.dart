import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/api/api_client.dart';
import '../../auth/repositories/auth_repository.dart';
import '../providers/server_provider.dart';

class ServerConfigScreen extends ConsumerStatefulWidget {
  const ServerConfigScreen({super.key});

  @override
  ConsumerState<ServerConfigScreen> createState() => _ServerConfigScreenState();
}

class _ServerConfigScreenState extends ConsumerState<ServerConfigScreen> {
  final _urlController = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  bool _loading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    ref.read(serverConfigProvider.notifier).load().then((_) {
      final saved = ref.read(serverConfigProvider);
      if (saved != null && _urlController.text.isEmpty) {
        _urlController.text = saved;
      }
    });
  }

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  Future<void> _connect() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() { _loading = true; _error = null; });

    try {
      final url = _urlController.text.trim();
      ApiClient.instance.updateBaseUrl(url);
      final repo = AuthRepository();
      await repo.getConfig();
      await ref.read(serverConfigProvider.notifier).setUrl(url);
      if (mounted) context.go('/login');
    } on Exception catch (e) {
      setState(() => _error = 'Connection failed: ${e.toString()}');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Form(
              key: _formKey,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  ClipRRect(
                      borderRadius: BorderRadius.circular(16),
                      child: SizedBox(
                        width: 80,
                        height: 80,
                        child: SvgPicture.asset('assets/images/logo.svg'),
                      ),
                    ),
                  const SizedBox(height: 16),
                  Text('生计', style: theme.textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  Text('生活成本计算器', style: theme.textTheme.bodyLarge?.copyWith(color: theme.colorScheme.outline)),
                  const SizedBox(height: 48),
                  TextFormField(
                    controller: _urlController,
                    decoration: const InputDecoration(
                      labelText: '后端地址',
                      hintText: 'http://192.168.x.x:8000',
                      prefixIcon: Icon(Icons.dns_outlined),
                    ),
                    keyboardType: TextInputType.url,
                    validator: (v) {
                      if (v == null || v.trim().isEmpty) return '请输入后端地址';
                      if (!v.trim().startsWith('http')) return '必须以 http:// 或 https:// 开头';
                      return null;
                    },
                  ),
                  const SizedBox(height: 8),
                  if (_error != null) Column(children: [Text('连接失败：', style: TextStyle(color: theme.colorScheme.error, fontWeight: FontWeight.bold)), Text(_error!, style: TextStyle(color: theme.colorScheme.error, fontSize: 12))],),
                  const SizedBox(height: 24),
                  FilledButton(
                    onPressed: _loading ? null : _connect,
                    child: _loading
                        ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                        : const Text('连接'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

