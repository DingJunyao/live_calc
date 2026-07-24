 import 'package:flutter/material.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 import 'package:go_router/go_router.dart';
 import '../providers/auth_provider.dart';
 
 class RegisterScreen extends ConsumerStatefulWidget {
   const RegisterScreen({super.key});
 
   @override
   ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
 }
 
 class _RegisterScreenState extends ConsumerState<RegisterScreen> {
   final _usernameController = TextEditingController();
   final _emailController = TextEditingController();
   final _passwordController = TextEditingController();
   final _phoneController = TextEditingController();
   final _inviteCodeController = TextEditingController();
   final _formKey = GlobalKey<FormState>();
   bool _showInviteCode = false;
 
   @override
   void dispose() {
     _usernameController.dispose();
     _emailController.dispose();
     _passwordController.dispose();
     _phoneController.dispose();
     _inviteCodeController.dispose();
     super.dispose();
   }
 
   Future<void> _register() async {
     if (!_formKey.currentState!.validate()) return;
     final success = await ref.read(authProvider.notifier).register(
       username: _usernameController.text.trim(),
       email: _emailController.text.trim(),
       password: _passwordController.text,
       phone: _phoneController.text.trim().isEmpty ? null : _phoneController.text.trim(),
       inviteCode: _inviteCodeController.text.trim().isEmpty ? null : _inviteCodeController.text.trim(),
     );
     if (success && mounted) context.go('/home');
   }
 
   @override
   Widget build(BuildContext context) {
     final theme = Theme.of(context);
     final authState = ref.watch(authProvider);
 
     return Scaffold(
       appBar: AppBar(title: const Text('注册')),
       body: SafeArea(
         child: SingleChildScrollView(
           padding: const EdgeInsets.all(24),
           child: Form(
             key: _formKey,
             child: Column(
               crossAxisAlignment: CrossAxisAlignment.stretch,
               children: [
                 TextFormField(
                   controller: _usernameController,
                   decoration: const InputDecoration(labelText: '用户名', prefixIcon: Icon(Icons.person_outline)),
                   validator: (v) {
                     if (v == null || v.trim().isEmpty) return '请输入用户名';
                     if (v.trim().length < 3) return '用户名至少 3 个字符';
                     return null;
                   },
                 ),
                 const SizedBox(height: 16),
                 TextFormField(
                   controller: _emailController,
                   decoration: const InputDecoration(labelText: '邮箱', prefixIcon: Icon(Icons.email_outlined)),
                   keyboardType: TextInputType.emailAddress,
                   validator: (v) {
                     if (v == null || v.trim().isEmpty) return '请输入邮箱';
                     if (!v.contains('@')) return '邮箱格式不正确';
                     return null;
                   },
                 ),
                 const SizedBox(height: 16),
                 TextFormField(
                   controller: _passwordController,
                   obscureText: true,
                   decoration: const InputDecoration(labelText: '密码', prefixIcon: Icon(Icons.lock_outline)),
                   validator: (v) => v == null || v.isEmpty ? '请输入密码' : null,
                 ),
                 const SizedBox(height: 16),
                 TextFormField(
                   controller: _phoneController,
                   decoration: const InputDecoration(labelText: '手机号（可选）', prefixIcon: Icon(Icons.phone_outlined)),
                   keyboardType: TextInputType.phone,
                 ),
                 const SizedBox(height: 8),
                 Row(
                   children: [
                     Checkbox(
                       value: _showInviteCode,
                       onChanged: (v) => setState(() => _showInviteCode = v ?? false),
                     ),
                     const Text('需要邀请码'),
                   ],
                 ),
                 if (_showInviteCode) ...[
                   const SizedBox(height: 8),
                   TextFormField(
                     controller: _inviteCodeController,
                     decoration: const InputDecoration(labelText: '邀请码', prefixIcon: Icon(Icons.card_giftcard_outlined)),
                   ),
                 ],
                 const SizedBox(height: 8),
                 if (authState.errorMessage != null)
                   Text(authState.errorMessage!, style: TextStyle(color: theme.colorScheme.error)),
                 const SizedBox(height: 24),
                 FilledButton(
                   onPressed: authState.status == AuthStatus.loading ? null : _register,
                   child: authState.status == AuthStatus.loading
                       ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                       : const Text('注册'),
                 ),
                 const SizedBox(height: 16),
                 TextButton(onPressed: () => context.go('/login'), child: const Text('已有账号？去登录')),
               ],
             ),
           ),
         ),
       ),
     );
   }
 }
