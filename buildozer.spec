[app]
title = Dziennik zajęć
package.name = dziennikzajec
package.domain = org.twojaorganizacja
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.1
requirements = python3,kivy,requests,certifi
orientation = portrait
fullscreen = 0

android.permissions = INTERNET
android.api = 33
android.minapi = 24
android.archs = arm64-v8a,armeabi-v7a

[buildozer]
log_level = 1
warn_on_root = 1
