import webbrowser
import logging
import urllib.parse
import threading

logger = logging.getLogger("neuromango.action")

def execute_action(action_str: str):
    """
    Parses and executes an action tag like 'OpenBrowser' or 'PlayYouTube=Rammstein'.
    Runs in a background thread to avoid blocking the main event loop or TTS generation.
    """
    def _run():
        try:
            parts = action_str.split("=", 1)
            command = parts[0].strip()
            arg = parts[1].strip() if len(parts) > 1 else ""
            
            if command == "SearchGoogle":
                logger.info(f"🌐 Выполняю команду: Ищу в Google ({arg})...")
                query = urllib.parse.quote(arg)
                webbrowser.open(f"https://www.google.com/search?q={query}")
            elif command == "PlayYouTube":
                logger.info(f"🎵 Выполняю команду: Включаю музыку на YouTube ({arg})...")
                import urllib.request
                import re
                try:
                    query = urllib.parse.quote(arg)
                    url = f"https://www.youtube.com/results?search_query={query}"
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    html = urllib.request.urlopen(req).read().decode('utf-8')
                    video_ids = re.findall(r"watch\?v=([a-zA-Z0-9_-]{11})", html)
                    if video_ids:
                        webbrowser.open(f"https://www.youtube.com/watch?v={video_ids[0]}")
                    else:
                        webbrowser.open(url) # Fallback
                except Exception as e:
                    logger.error(f"YouTube parse error: {e}")
                    webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(arg)}")
            elif command == "EditFile" or command == "CreateFile":
                path_content = arg.split("|", 1)
                if len(path_content) == 2:
                    import os
                    path = os.path.abspath(path_content[0].strip())
                    content = path_content[1]
                    
                    if path.endswith(".py") and "neuromango" in path.lower():
                        logger.error(f"❌ Security Block: AI attempted to modify its own source code: {path}")
                        return

                    if command == "CreateFile":
                        with open(path, "w", encoding="utf-8") as f:
                            f.write(content.strip())
                        logger.info(f"📁 Выполняю команду: Создаю файл {path}")
                    else:
                        with open(path, "a", encoding="utf-8") as f:
                            f.write("\n" + content.strip())
                        logger.info(f"📁 Выполняю команду: Добавляю текст в файл {path}")
            elif command == "OpenFile":
                import os
                path = os.path.abspath(arg.strip())
                os.startfile(path)
                logger.info(f"📁 Выполняю команду: Открываю файл {path}")
            elif command == "MoveFile":
                import shutil, os
                src_dest = arg.split("|", 1)
                if len(src_dest) == 2:
                    src = os.path.abspath(src_dest[0].strip())
                    dest = os.path.abspath(src_dest[1].strip())
                    shutil.move(src, dest)
                    logger.info(f"📁 Выполняю команду: Перемещаю файл {src} -> {dest}")
            elif command == "QueueMusic":
                import shared_state
                logger.info(f"🎵 Выполняю команду: Заказ музыки ({arg})")
                if hasattr(shared_state, 'music_service') and shared_state.music_service:
                    if hasattr(shared_state, 'main_loop') and shared_state.main_loop:
                        import asyncio
                        asyncio.run_coroutine_threadsafe(shared_state.music_service.add_to_queue(arg), shared_state.main_loop)
                    else:
                        import asyncio
                        asyncio.create_task(shared_state.music_service.add_to_queue(arg))
                else:
                    logger.error("❌ Music service is not initialized!")
            elif command == "SendTwitch":
                import shared_state
                import asyncio
                logger.info(f"✉️ Выполняю команду: Пишу в Twitch чат ({arg})")
                if hasattr(shared_state, 'twitch_service') and shared_state.twitch_service:
                    if hasattr(shared_state, 'main_loop') and shared_state.main_loop:
                        asyncio.run_coroutine_threadsafe(shared_state.twitch_service.send_message(arg), shared_state.main_loop)
                    else:
                        asyncio.create_task(shared_state.twitch_service.send_message(arg))
                else:
                    logger.error("❌ Twitch service is not initialized!")
            elif command == "PlaySound":
                import shared_state
                logger.info(f"🎵 Выполняю команду: Играю звук {arg}")
                if hasattr(shared_state, 'audio_service') and shared_state.audio_service is not None:
                    shared_state.audio_service.play_sound_async(arg)
            elif command == "RunCommand":
                import subprocess
                logger.info(f"💻 Выполняю команду ОС: {arg.strip()}")
                subprocess.Popen(arg.strip(), shell=True)

            elif command == "RunAdminCommand":
                import ctypes
                logger.info(f"🛡️ Выполняю команду ОС (Администратор): {arg.strip()}")
                # Trigger UAC prompt to run the command as Administrator
                ctypes.windll.shell32.ShellExecuteW(None, "runas", "cmd.exe", f"/c {arg.strip()}", None, 1)
            elif command == "MouseMove":
                import pyautogui
                x_y = arg.split("|", 1)
                if len(x_y) == 2:
                    try:
                        x = int(x_y[0].strip())
                        y = int(x_y[1].strip())
                        pyautogui.moveTo(x, y, duration=0.2)
                        logger.info(f"🖱️ Выполняю команду: Двигаю курсор в ({x}, {y})")
                    except ValueError:
                        logger.error("MouseMove requires integer coordinates")
            elif command == "MouseClick":
                import pyautogui
                button = arg.strip().lower() if arg else "left"
                if button not in ["left", "right", "middle"]:
                    button = "left"
                pyautogui.click(button=button)
                logger.info(f"🖱️ Выполняю команду: Клик мышью ({button})")
            elif command == "KeyboardType":
                import pyautogui
                pyautogui.write(arg.strip(), interval=0.05)
                logger.info(f"⌨️ Выполняю команду: Печатаю текст '{arg.strip()}'")
            elif command == "KeyboardPress":
                import pyautogui
                keys = [k.strip() for k in arg.split("+")]
                pyautogui.hotkey(*keys)
                logger.info(f"⌨️ Выполняю команду: Нажимаю клавиши {keys}")
            elif command == "ToggleHeartbeat":
                import requests
                import config
                try:
                    state_res = requests.get(f"http://127.0.0.1:{config.PORT}/api/modules").json()
                    is_enabled = state_res.get("heartbeat", True)
                    new_state = not is_enabled
                    requests.post(f"http://127.0.0.1:{config.PORT}/api/modules/toggle?module=heartbeat&enabled={str(new_state).lower()}")
                    status = "ВКЛЮЧЕН" if new_state else "ОТКЛЮЧЕН"
                    logger.info(f"💓 Фоновый режим (Heartbeat) {status} по инициативе ИИ!")
                except Exception as e:
                    logger.error(f"❌ Ошибка переключения Heartbeat: {e}")
            else:
                logger.warning(f"⚠️ Неизвестная команда Action: {command}")
        except Exception as e:
            logger.error(f"❌ Ошибка выполнения команды {action_str}: {e}")

    # Запускаем в отдельном потоке, чтобы не тормозить генерацию аудио
    threading.Thread(target=_run, daemon=True).start()
