import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../providers/merchant_provider.dart';
import '../../../shared/widgets/loading_indicator.dart';

class MerchantMapScreen extends ConsumerWidget {
  const MerchantMapScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final state = ref.watch(merchantListProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Merchant Map')),
      body: state.loading
          ? const LoadingIndicator()
          : FlutterMap(
              options: MapOptions(
                initialCenter: const LatLng(39.9042, 116.4074),
                initialZoom: 11.0,
              ),
              children: [
                TileLayer(
                  urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                  userAgentPackageName: 'livecalc_mobile',
                ),
                MarkerLayer(
                  markers: state.items
                      .where((m) => m.latitude != null && m.longitude != null)
                      .map((m) => Marker(
                            point: LatLng(m.latitude!, m.longitude!),
                            child: GestureDetector(
                              onTap: () => ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(content: Text(m.name)),
                              ),
                              child: Icon(Icons.store, color: theme.colorScheme.primary, size: 32),
                            ),
                          ))
                      .toList(),
                ),
              ],
            ),
    );
  }
}
