 import 'package:flutter/material.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 import 'package:go_router/go_router.dart';
 import '../providers/auth_provider.dart';
 
 class LoginScreen extends ConsumerStatefulWidget {
   const LoginScreen({super.key});
 
   @override
   ConsumerState<LoginScreen> createState() => _LoginScreenState();
 }
 
 class _LoginScreenState extends ConsumerState<LoginScreen> {
   final _usernameController = TextEditingController();
   final _passwordController = TextEditingController();
   final _formKey = GlobalKey<FormState>();
 
   @override
   void dispose() {
     _usernameController.dispose();
     _passwordController.dispose();
     super.dispose();
   }
 
   Future<void> _login() async {
     if (!_formKey.currentState!.validate()) return;
     final success = await ref.read(authProvider.notifier).login(
       _usernameController.text.trim(), _passwordController.text,
     );
     if (success && mounted) context.go('/home');
   }
 
   @override
   Widget build(BuildContext context) {
     final theme = Theme.of(context);
     final authState = ref.watch(authProvider);
 
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
                   Icon(Icons.lock_outline, size: 48, color: theme.colorScheme.primary),
                   const SizedBox(height: 24),
                   Text('登录', style: theme.textTheme.headlineSmall),
                   const SizedBox(height: 8),
                   Text('请输入账号密码', style: theme.textTheme.bodyMedium?.copyWith(color: theme.colorScheme.outline)),
                   const SizedBox(height: 32),
                   TextFormField(
                     controller: _usernameController,
                     decoration: const InputDecoration(labelText: '用户名', prefixIcon: Icon(Icons.person_outline)),
                     validator: (v) => v == null || v.trim().isEmpty ? '请输入用户名' : null,
                   ),
                   const SizedBox(height: 16),
                   TextFormField(
                     controller: _passwordController,
                     obscureText: true,
                     decoration: const InputDecoration(labelText: '密码', prefixIcon: Icon(Icons.lock_outline)),
                     validator: (v) => v == null || v.isEmpty ? '请输入密码' : null,
                   ),
                   const SizedBox(height: 8),
                   if (authState.errorMessage != null)
                     Text(authState.errorMessage!, style: TextStyle(color: theme.colorScheme.error)),
                   const SizedBox(height: 24),
                   FilledButton(
                     onPressed: authState.status == AuthStatus.loading ? null : _login,
                     child: authState.status == AuthStatus.loading
                         ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                         : const Text('登录'),
                   ),
                   const SizedBox(height: 16),
                   TextButton(onPressed: () => context.go('/register'), child: const Text('没有账号？去注册')),
                   TextButton(onPressed: () => context.go('/server-config'), child: const Text('更换服务器')),
                 ],
               ),
             ),
           ),
         ),
       ),
     );
   }
 }
