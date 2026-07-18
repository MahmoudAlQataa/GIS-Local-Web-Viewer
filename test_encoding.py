path_dbf = r"F:\Mahmoud\Projects\WEP\GIS_wep_app\data_layers\shelters_fixed\shelters.dbf"

with open(path_dbf, "rb") as f:
    header = f.read(32)
    num_records = int.from_bytes(header[4:8], "little")
    header_size = int.from_bytes(header[8:10], "little")
    print("Num records:", num_records, "Header size:", header_size)

    num_fields = (header_size - 33) // 32
    print("Num fields:", num_fields)

    for i in range(num_fields):
        f.seek(32 + i * 32)
        field_desc = f.read(32)
        name = field_desc[:11].split(b'\x00')[0]
        print(f"Field {i}: {name}")