// Mirror Pupil — Utility Functions
import 'package:intl/intl.dart';

String formatCurrency(double amount) {
  final formatter = NumberFormat.currency(symbol: '\$', decimalDigits: 2);
  return formatter.format(amount);
}

String formatTimeAgo(DateTime dateTime) {
  final now = DateTime.now();
  final difference = now.difference(dateTime);

  if (difference.inSeconds < 60) {
    return '${difference.inSeconds}s ago';
  } else if (difference.inMinutes < 60) {
    return '${difference.inMinutes}m ago';
  } else if (difference.inHours < 24) {
    return '${difference.inHours}h ago';
  } else if (difference.inDays < 7) {
    return '${difference.inDays}d ago';
  } else {
    final formatter = DateFormat('MMM d');
    return formatter.format(dateTime);
  }
}

String shortenKey(String key) {
  if (key.length <= 12) return key;
  return '${key.substring(0, 6)}...${key.substring(key.length - 4)}';
}
