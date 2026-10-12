from pywinauto import Desktop

class LuluUIScanner:
    def scan_window(self, exact_window_title):
        """
        Scans visible windows matching exact_window_title and reads all text + accessibility names.
        """
        elements = []
        try:
            desktop = Desktop(backend="uia")
            for win in desktop.windows():
                if win.window_text().strip() == exact_window_title and win.is_visible():
                    for ctrl in win.descendants():
                        ctrl_type = ctrl.element_info.control_type
                        
                        # Combine both window_text and UIA Accessible Name so neither is missed
                        t1 = (ctrl.window_text() or "").strip()
                        t2 = (ctrl.element_info.name or "").strip()
                        combined_text = f"{t1} | {t2}".strip(" |")

                        if combined_text:
                            rect = ctrl.rectangle()
                            center_x = (rect.left + rect.right) // 2
                            center_y = (rect.top + rect.bottom) // 2
                            elements.append({
                                "text": combined_text,
                                "type": ctrl_type,
                                "x": center_x,
                                "y": center_y
                            })
        except Exception as e:
            print(f"[Scanner Warning]: {e}")
        return elements

    def find_element_center(self, elements, target_button_text):
        """Finds the target Button's (x, y) center."""
        for el in elements:
            if el["type"] == "Button" and target_button_text.lower() in el["text"].lower():
                return el["x"], el["y"]
        return None

    def is_text_on_screen(self, elements, expected_status_text):
        """Checks if the '(Done)' text has appeared on the button."""
        for el in elements:
            if expected_status_text.lower() in el["text"].lower():
                return True
        return False