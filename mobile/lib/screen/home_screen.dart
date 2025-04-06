import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:get/get.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'feature/conversation/create_situation_screen.dart';

import '../helper/ad_helper.dart';
import '../helper/global.dart';
import '../helper/pref.dart';
import '../model/home_type.dart';
import '../widgets/home_card.dart';

/// 📌 **Home Screen**
///
/// - Displays the main dashboard of the app
/// - Supports Dark Mode toggle
/// - Integrates Ads at the bottom
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  /// 🔹 **Dark Mode State**
  ///
  /// - Observes whether dark mode is enabled
  /// - Uses `Get.isDarkMode.obs` instead of `Pref.isDarkMode.obs` to avoid bugs
  final _isDarkMode = Get.isDarkMode.obs;

  // Mock user data - replace with actual user data from your backend
  final String _userName = "John Doe";
  final String _userEmail = "john.doe@example.com";
  final String _userAvatar =
      "https://ui-avatars.com/api/?name=John+Doe&background=0D8ABC&color=fff";

  @override
  void initState() {
    super.initState();

    // 🔄 **Enable Fullscreen Edge-to-Edge UI**
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);

    // 🚀 **Disable Onboarding for Future Launches**
    Pref.showOnboarding = false;
  }

  @override
  Widget build(BuildContext context) {
    // 📌 **Initialize Device Size for Responsive UI**
    mq = MediaQuery.sizeOf(context);

    return Scaffold(
      // 📌 **App Bar**
      appBar: AppBar(
        title: const Text(appName),
        elevation: 0,
        backgroundColor: Colors.transparent,

        // 🌙 **Dark Mode Toggle Button**
        actions: [
          IconButton(
            padding: const EdgeInsets.only(right: 10),
            onPressed: () {
              // 🔄 **Toggle Theme Mode**
              Get.changeThemeMode(
                _isDarkMode.value ? ThemeMode.light : ThemeMode.dark,
              );

              // 🔄 **Update Theme State & Save Preference**
              _isDarkMode.value = !_isDarkMode.value;
              Pref.isDarkMode = _isDarkMode.value;
            },
            icon: Obx(() => Icon(
                  _isDarkMode.value
                      ? Icons.brightness_2_rounded // 🌙 Dark Mode Icon
                      : Icons.brightness_5_rounded, // ☀️ Light Mode Icon
                  size: 26,
                )),
          ),
        ],
      ),

      // 📌 **Bottom Ad Banner**
      bottomNavigationBar: AdHelper.nativeBannerAd(),

      // 📌 **Main Body**
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Theme.of(context).brightness == Brightness.dark
                  ? Colors.blue.shade900.withOpacity(0.3)
                  : Colors.blue.shade50,
              Theme.of(context).brightness == Brightness.dark
                  ? Colors.purple.shade900.withOpacity(0.3)
                  : Colors.purple.shade50,
            ],
          ),
        ),
        child: ListView(
          padding: EdgeInsets.symmetric(
            horizontal: mq.width * .04,
            vertical: mq.height * .015,
          ),
          children: [
            // User Profile Card
            Card(
              elevation: 2,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16),
              ),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    CircleAvatar(
                      radius: 30,
                      backgroundImage: NetworkImage(_userAvatar),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Welcome back,',
                            style: TextStyle(
                              fontSize: 14,
                              color: Colors.grey.shade600,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            _userName,
                            style: const TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            _userEmail,
                            style: TextStyle(
                              fontSize: 12,
                              color: Colors.grey.shade600,
                            ),
                          ),
                        ],
                      ),
                    ),
                    IconButton(
                      onPressed: () {
                        HomeType.profile.onTap();
                      },
                      icon: Icon(
                        Icons.edit_outlined,
                        color: Colors.blue.shade700,
                      ),
                    ),
                  ],
                ),
              ),
            ).animate().fadeIn(duration: 600.ms).slideY(begin: 0.2, end: 0),

            const SizedBox(height: 24),

            // Learning Tools Section
            const Padding(
              padding: EdgeInsets.only(left: 4, bottom: 12),
              child: Text(
                'Learning Tools',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ).animate().fadeIn(duration: 600.ms, delay: 400.ms),

            // Menu Items
            ...HomeType.values.map((e) => HomeCard(homeType: e)),
          ],
        ),
      ),
    );
  }

  // 📊 Build progress item
  Widget _buildProgressItem({
    required IconData icon,
    required String title,
    required String value,
    required Color color,
  }) {
    return Column(
      children: [
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: color.withOpacity(0.1),
            shape: BoxShape.circle,
          ),
          child: Icon(
            icon,
            color: color,
            size: 24,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          value,
          style: const TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          title,
          style: TextStyle(
            fontSize: 12,
            color: Colors.grey.shade600,
          ),
        ),
      ],
    );
  }
}
