import tkinter as tk
import pyglet

pyglet.font.add_file("BoschSans-Regular.ttf")
root = tk.Tk()

root.title("Berichtsheft Generator")
root.geometry("600x600")
root.config(bg="lightgray")
root.resizable(False, False)

tk.Label(root, text="Berichtsheft Generator", font=("BoschSans-Regular", 24, "bold"), bg="lightgray").pack(pady=20)










root.mainloop()