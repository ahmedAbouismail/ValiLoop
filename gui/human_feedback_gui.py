import customtkinter
import json
import time
from typing import Dict, Any

# Configure CustomTkinter appearance
customtkinter.set_appearance_mode("System")  # System, Light, Dark
customtkinter.set_default_color_theme("blue")  # blue, dark-blue, green

class HumanFeedbackGUI:
    def __init__(self):
        self.result = None
        self.start_time = None

    def launch_feedback_gui(self, raw_text: str, json_output: Dict[str, Any],
                            domain: str, iteration: int) -> Dict[str, Any]:
        """
        Launch modern GUI for human feedback collection

        Returns:
            {
                'action': 'approve' | 'correct',
                'feedback': str,
                'response_time': float
            }
        """
        self.start_time = time.time()

        # Create main window
        self.root = customtkinter.CTk()
        self.root.title("JSON Strukturierungs-Agent - Human Review")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 600)

        # Configure grid weights for responsive design
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)  # Main content area

        self._create_header(domain, iteration)
        self._create_main_content(raw_text, json_output)
        self._create_feedback_section()
        self._create_action_buttons()

        # Center window on screen
        self._center_window()

        # Make window modal and wait for user action
        self.root.grab_set()
        self.root.focus_set()
        self.root.mainloop()

        return self.result

    def _create_header(self, domain: str, iteration: int):
        """Create header with domain and iteration info"""
        header_frame = customtkinter.CTkFrame(self.root)
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        header_frame.grid_columnconfigure(1, weight=1)

        # Title
        title_label = customtkinter.CTkLabel(
            header_frame,
            text="Human Review Required",
            font=customtkinter.CTkFont(size=24, weight="bold")
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=10)

        # Domain info
        domain_label = customtkinter.CTkLabel(
            header_frame,
            text=f"Domain: {domain.capitalize()}",
            font=customtkinter.CTkFont(size=14, weight="bold")
        )
        domain_label.grid(row=1, column=0, padx=20, pady=5, sticky="w")

        # Iteration info
        iteration_label = customtkinter.CTkLabel(
            header_frame,
            text=f"Iteration: {iteration}",
            font=customtkinter.CTkFont(size=14, weight="bold")
        )
        iteration_label.grid(row=1, column=2, padx=20, pady=5, sticky="e")

    def _create_main_content(self, raw_text: str, json_output: Dict[str, Any]):
        """Create side-by-side content panels"""
        content_frame = customtkinter.CTkFrame(self.root)
        content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_columnconfigure(1, weight=1)
        content_frame.grid_rowconfigure(0, weight=1)

        # Original Text Panel with improved formatting
        self._create_text_panel(
            content_frame,
            "Original Text",
            raw_text,
            0, 0,
            readonly=True,
            is_json=False
        )

        # JSON Output Panel with special formatting
        formatted_json = self._format_json_for_display(json_output)
        self._create_text_panel(
            content_frame,
            "JSON Output",
            formatted_json,
            0, 1,
            readonly=True,
            is_json=True
        )

    def _create_text_panel(self, parent, title: str, content: str,
                           row: int, column: int, readonly: bool = True, is_json: bool = False):
        """Create a text panel with title and scrollable content"""
        panel_frame = customtkinter.CTkFrame(parent)
        panel_frame.grid(row=row, column=column, sticky="nsew", padx=10, pady=10)
        panel_frame.grid_rowconfigure(1, weight=1)
        panel_frame.grid_columnconfigure(0, weight=1)

        # Panel title
        title_label = customtkinter.CTkLabel(
            panel_frame,
            text=title,
            font=customtkinter.CTkFont(size=18, weight="bold")
        )
        title_label.grid(row=0, column=0, pady=(15, 10), sticky="w", padx=15)

        # Choose font based on content type
        if is_json:
            # Use monospace font for JSON with larger size for better readability
            text_font = customtkinter.CTkFont(family="Consolas", size=14)
        else:
            # Use regular font for original text with larger size
            text_font = customtkinter.CTkFont(family="Segoe UI", size=15)

        # Text content with improved styling
        text_widget = customtkinter.CTkTextbox(
            panel_frame,
            font=text_font,
            wrap="word",
            corner_radius=8
        )
        text_widget.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))

        # Insert content
        text_widget.insert("0.0", content)

        if readonly:
            text_widget.configure(state="disabled")

    def _format_json_for_display(self, json_data: Dict[str, Any]) -> str:
        """Format JSON with extra spacing for better readability"""
        # Convert to JSON string with proper indentation
        json_str = json.dumps(json_data, indent=3, ensure_ascii=False)

        # Add extra line breaks for better visual separation
        lines = json_str.split('\n')
        formatted_lines = []

        for i, line in enumerate(lines):
            formatted_lines.append(line)

            # Add extra spacing after opening braces and before closing braces
            if line.strip().endswith('{') or line.strip().endswith('['):
                formatted_lines.append('')
            elif i < len(lines) - 1 and (lines[i + 1].strip().startswith('}') or lines[i + 1].strip().startswith(']')):
                formatted_lines.append('')

        return '\n'.join(formatted_lines)

    def _create_feedback_section(self):
        """Create feedback input section"""
        feedback_frame = customtkinter.CTkFrame(self.root)
        feedback_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        feedback_frame.grid_columnconfigure(0, weight=1)
        feedback_frame.grid_rowconfigure(1, weight=1)

        # Feedback title and instructions
        feedback_label = customtkinter.CTkLabel(
            feedback_frame,
            text="Your Feedback",
            font=customtkinter.CTkFont(size=16, weight="bold")
        )
        feedback_label.grid(row=0, column=0, pady=(15, 5), sticky="w", padx=15)

        instruction_label = customtkinter.CTkLabel(
            feedback_frame,
            text="Compare the original text with the JSON output. Provide feedback on accuracy and completeness:",
            font=customtkinter.CTkFont(size=12),
            text_color="gray"
        )
        instruction_label.grid(row=0, column=0, pady=(35, 10), sticky="w", padx=15)

        # Feedback text area
        self.feedback_textbox = customtkinter.CTkTextbox(
            feedback_frame,
            height=120,
            font=customtkinter.CTkFont(size=12),
            #placeholder_text="Enter your feedback here... (Leave empty to approve)"
        )
        self.feedback_textbox.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 15))
        self.feedback_textbox.focus()

    def _create_action_buttons(self):
        """Create action buttons"""
        button_frame = customtkinter.CTkFrame(self.root)
        button_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 20))
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        # Approve Button
        approve_button = customtkinter.CTkButton(
            button_frame,
            text="✓ Approve",
            font=customtkinter.CTkFont(size=14, weight="bold"),
            height=45,
            fg_color="#28a745",
            hover_color="#218838",
            command=self._handle_approve
        )
        approve_button.grid(row=0, column=0, padx=15, pady=15, sticky="ew")

        # Provide Corrections Button
        correct_button = customtkinter.CTkButton(
            button_frame,
            text="📝 Provide Corrections",
            font=customtkinter.CTkFont(size=14, weight="bold"),
            height=45,
            fg_color="#ffc107",
            hover_color="#e0a800",
            text_color="black",
            command=self._handle_corrections
        )
        correct_button.grid(row=0, column=1, padx=15, pady=15, sticky="ew")

    def _center_window(self):
        """Center window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def _handle_approve(self):
        """Handle approve action"""
        response_time = time.time() - self.start_time
        feedback = self.feedback_textbox.get("0.0", "end-1c").strip()

        self.result = {
            'action': 'approve',
            'feedback': feedback if feedback else None,
            'response_time': response_time
        }
        self.root.quit()
        self.root.destroy()

    def _handle_corrections(self):
        """Handle corrections action"""
        response_time = time.time() - self.start_time
        feedback = self.feedback_textbox.get("0.0", "end-1c").strip()

        if not feedback:
            # Show warning if no feedback provided
            self._show_warning("Please provide feedback for corrections.")
            return

        self.result = {
            'action': 'correct',
            'feedback': feedback,
            'response_time': response_time
        }
        self.root.quit()
        self.root.destroy()

    def _show_warning(self, message: str):
        """Show warning dialog"""
        warning_window = customtkinter.CTkToplevel(self.root)
        warning_window.title("Warning")
        warning_window.geometry("400x150")
        warning_window.resizable(False, False)
        warning_window.grab_set()

        # Center warning window
        warning_window.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 200
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 75
        warning_window.geometry(f"400x150+{x}+{y}")

        warning_label = customtkinter.CTkLabel(
            warning_window,
            text=message,
            font=customtkinter.CTkFont(size=14),
            wraplength=350
        )
        warning_label.pack(pady=30)

        ok_button = customtkinter.CTkButton(
            warning_window,
            text="OK",
            width=100,
            command=warning_window.destroy
        )
        ok_button.pack(pady=10)


def launch_human_feedback_gui(raw_text: str, json_output: Dict[str, Any],
                              domain: str, iteration: int) -> Dict[str, Any]:
    gui = HumanFeedbackGUI()
    return gui.launch_feedback_gui(raw_text, json_output, domain, iteration)