import base64


def make_chart(data: list[dict]) -> str:
    # THis is where Chaitanya comes it!!
    # DO THIS!!
    pass



if __name__ == '__main__':
    # Inputs
    # List of dictionaries
    data = [
        {"age_group": "0-17", "admissions_per_1000": 75},
        {"age_group": "18-34", "admissions_per_1000": 112},
        {"age_group": "35-49", "admissions_per_1000": 134},
        {"age_group": "50-64", "admissions_per_1000": 187},
        {"age_group": "65-74", "admissions_per_1000": 243},
        {"age_group": "75-84", "admissions_per_1000": 312},
        {"age_group": "85+", "admissions_per_1000": 410},
    ]
    result = make_chart(data)
    # Outputs
    # base64encoded string of a chart
    # Decode the base64 string into bytes
    image_data = base64.b64decode(result)

    # Write the binary data to a file (e.g., PNG)
    with open("output_image.png", "wb") as f:
        f.write(image_data)