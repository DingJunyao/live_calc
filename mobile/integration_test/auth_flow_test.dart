import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  group('认证流程', () {
    testWidgets('服务器配置页显示', (tester) async {
      await tester.pumpAndSettle();
      expect(find.text('服务器地址'), findsOneWidget);
      expect(find.text('连接服务器'), findsOneWidget);
    });
  });
}
