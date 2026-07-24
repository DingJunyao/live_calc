import 'package:flutter/material.dart';

class PriceListScreen extends StatelessWidget {
  const PriceListScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('价格记录')),
      body: const Center(child: Text('价格记录 - 待实现')),
      floatingActionButton: FloatingActionButton(
        onPressed: () {},
        child: const Icon(Icons.add),
      ),
    );
  }
}
