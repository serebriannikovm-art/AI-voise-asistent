[app]

# =========================================
# APP INFO
# =========================================
title = Voice AI Assistant

package.name = voiceai
package.domain = org.voice.ai

source.dir = .

source.include_exts = py,png,jpg,jpeg,kv,json,txt,atlas

version = 1.0

orientation = portrait

fullscreen = 0

# =========================================
# INCLUDE FILES
# =========================================
source.exclude_dirs = venv,.venv,__pycache__,build,.buildozer,.git

# =========================================
# REQUIREMENTS
# =========================================
requirements = python3,kivy==2.3.1,vosk,pyaudio,openai,httpx,sdl2,pyjnius

# =========================================
# ANDROID
# =========================================
android.api = 34
android.minapi = 24

android.ndk = 25b

android.archs = arm64-v8a, armeabi-v7a

android.enable_androidx = True

android.copy_libs = 1

# =========================================
# PERMISSIONS
# =========================================
android.permissions = INTERNET,RECORD_AUDIO,MODIFY_AUDIO_SETTINGS,WAKE_LOCK

# =========================================
# LOGS
# =========================================
android.logcat_filters = *:S python:D

# =========================================
# APK
# =========================================
android.debug_artifact = apk
android.release_artifact = apk

# =========================================
# SPLASH / ICON
# =========================================
# presplash.filename = presplash.png
# icon.filename = icon.png

android.presplash_color = #202020

# =========================================
# PERFORMANCE
# =========================================
android.allow_backup = True

# =========================================
# KIVY
# =========================================
osx.kivy_version = 2.3.1

# =========================================
# P4A
# =========================================
p4a.branch = master

# =========================================
# IOS
# =========================================
ios.kivy_ios_url = https://github.com/kivy/kivy-ios
ios.kivy_ios_branch = master

ios.ios_deploy_url = https://github.com/phonegap/ios-deploy
ios.ios_deploy_branch = 1.12.2

ios.codesign.allowed = false


# =========================================
# BUILDOZER
# =========================================
[buildozer]

log_level = 2

warn_on_root = 1