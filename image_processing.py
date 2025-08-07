from PIL import Image
import numpy as np
from collections import Counter
import matplotlib.pyplot as plt
from matplotlib import colors


color_map = {
        0: 'red',
        1: 'yellow',
        2: 'blue',
        3: '#4B0082',     # dioxazine purple
        4: '#90EE90',     # light green
        5: 'black',
        6: 'gray',
        7: '#8A3324',     # burnt umber (reddish-brown)
        8: '#FF6100',     # cadmium orange hue
        9: '#006400',     # dark green
        10: 'white',
    }

def load_and_process_image(image_path, output_size=(100, 100)):
    img = Image.open(image_path).convert("RGB")
    img = img.resize(output_size)
    img_np = np.array(img)

    return img_np / 255.0  # Normalize RGB



def compute_dominant_color_matrix(color_matrix, region_size=5, alpha=10):
    """
    Uses color distance matching to an extended paint palette with weighted random sampling.
    Returns a 2D matrix of color IDs.
    """
    height, width, _ = color_matrix.shape
    output_rows = height // region_size
    output_cols = width // region_size
    output_matrix = np.zeros((output_rows, output_cols), dtype=int)

    # Extended palette (normalized RGB)
    palette = {
        0: np.array([1.0, 0.0, 0.0]),           # red
        1: np.array([1.0, 1.0, 0.0]),           # yellow
        2: np.array([0.0, 0.0, 1.0]),           # blue
        3: np.array([0.294, 0.0, 0.51]),        # dioxazine purple
        4: np.array([0.565, 0.933, 0.565]),     # light green
        5: np.array([0.0, 0.0, 0.0]),           # black
        6: np.array([0.20, 0.40, 0.20]),        # greenish grey
        7: np.array([0.541, 0.2, 0.141]),       # burnt umber
        8: np.array([1.0, 0.38, 0.012]),        # cadmium orange hue
        9: np.array([0.0, 0.392, 0.0]),         # dark green
        10: np.array([1.0, 1.0, 1.0]),          # white
    }

    for i in range(output_rows):
        for j in range(output_cols):
            region = color_matrix[
                i * region_size:(i + 1) * region_size,
                j * region_size:(j + 1) * region_size
            ]
            avg_rgb = region.mean(axis=(0, 1))

            # Compute distances and turn into inverse-weighted probabilities
            distances = {k: np.linalg.norm(avg_rgb - v) for k, v in palette.items()}
            inv_weights = {k: np.exp(-alpha * d) for k, d in distances.items()}

            total_weight = sum(inv_weights.values())
            probs = {k: w / total_weight for k, w in inv_weights.items()}

            # Use probabilities to pick a color
            ids = list(probs.keys())
            weights = list(probs.values())
            chosen_id = np.random.choice(ids, p=weights)
            output_matrix[i, j] = chosen_id

    return output_matrix



def visualize_dot_matrix(dot_matrix, dot_size=100):
    """
    Visualizes a matrix of color IDs as dots on a white canvas using imshow.
    """

    # Map the dot_matrix values to actual RGB colors
    height, width = dot_matrix.shape
    image = np.zeros((height, width, 3), dtype=np.uint8)

    for color_id, color in color_map.items():
        # Convert color to RGB tuple using matplotlib.colors.to_rgb
        rgb_color = np.array(colors.to_rgb(color)) * 255
        image[dot_matrix == color_id] = rgb_color

    # Plot using imshow for much faster rendering
    fig, ax = plt.subplots()
    ax.imshow(image)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect('equal')
    plt.show()

test_color_map = {
    0: 'black',  # circle
    1: 'red',    # square
    2: 'blue',   # line
}

def generate_pointillism_gcode(color_matrix, feedrate=800, z_height=0):
    gcode = []
    gcode.append("G90") # absolute coords
    gcode.append("G10 L20 P1 X0 Y0 Z0")
    gcode.append("G1 Z3 F500")  # retract from canvas
    gcode.append("G0 X-100 F800")
    gcode.append("M0 ; Pause to change color")  # Pause for manual color change


    for color_index in range(11): #skip white
        gcode.append(f"; --- Starting color: {color_map[color_index]} ---")

        y_distance = 0
        for i in range(color_matrix.shape[0]):#rows
            y_distance -= 3
            x_distance = 0
            for j in range(color_matrix.shape[1]):  #columns
                x_distance += 3
                value = color_matrix[i, j]
                if value == color_index:
                    gcode.append(f"G0 X{x_distance:.2f} F{feedrate}")
                    gcode.append(f"G0 Y{y_distance:.2f} F{feedrate}")
                    gcode.append(";DISPENSE")  # stepper motor dispenses
                    gcode.append(f"G1 Z{z_height:.2f} F500")  # Move to canvas
                    gcode.append("G1 Z3 F500") #retract from canvas

        gcode.append(f"G1 Z5 F1000") #  Raise Z first (safe height)
        gcode.append(f"G0 X-100 F800")  # Then rapid move to home position
        gcode.append(f"G0 Y0 F800")
        gcode.append("M0 ; Pause to change color")  #Pause for manual color change

    return gcode

def list_colors_used(dot_matrix):
    unique_ids = np.unique(dot_matrix)
    used_colors = [(color_id, color_map[color_id]) for color_id in unique_ids]
    print("🎨 Colors used in this image:")
    for color_id, name in used_colors:
        print(f"  ID {color_id}: {name}")
    return used_colors

# === Example usage ===
if __name__ == "__main__":
    GENERATE_GCODE = True
    VISUALIZE_DOT_MATRIX = True

    image_path = "images/THEIMAGE.jpeg"  # Replace with image path
    color_matrix = load_and_process_image(image_path, output_size=(330, 415))
    dot_matrix = compute_dominant_color_matrix(color_matrix, region_size=5)

    list_colors_used(dot_matrix)

    if VISUALIZE_DOT_MATRIX:
        visualize_dot_matrix(dot_matrix, dot_size=5)

    if GENERATE_GCODE:
        #Generate G-code
        gcode_lines = generate_pointillism_gcode(dot_matrix)
        output_path = "output/pointillism.gcode"
        with open(output_path, "w") as f:
            for line in gcode_lines:
                f.write(line + "\n")

        print(f"G-code written to {output_path}")
