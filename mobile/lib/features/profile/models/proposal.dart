class Proposal {
  final int id;
  final String title;
  final String status; // pending, approved, rejected
  final String? description;
  final String createdAt;

  const Proposal({
    required this.id,
    required this.title,
    required this.status,
    this.description,
    required this.createdAt,
  });

  factory Proposal.fromJson(Map<String, dynamic> json) {
    return Proposal(
      id: json['id'] as int,
      title: json['title'] as String? ?? '',
      status: json['status'] as String? ?? 'pending',
      description: json['description'] as String?,
      createdAt: json['created_at'] as String? ?? '',
    );
  }
}
