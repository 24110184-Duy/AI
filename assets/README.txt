Huong dan them asset PNG
========================

Game van chay duoc neu khong co asset. Neu co PNG, AssetLoader se tu scan trong assets/.
Map hien tai duoc sinh theo dang xa ban thanh pho:
- Duong van la grid 1 o de thuat toan chay on dinh.
- Cong trinh la CityLot nhieu o: 2x1, 2x2, 2x3, 3x2, 3x4, 4x4...
- Moi lot co anchor, footprint, district, height, asset_key.

Thu muc PNG:

roads/
- road.png
- road_straight.png
- road_turn.png
- road_cross.png

buildings/
- building_1.png
- building_1_2x1.png
- building_1_house_2x2.png
- building_2_2x3.png
- building_3_3x2.png
- building_4_3x4.png
- building_5_4x3.png
- building_6_4x4.png
- hospital_4x3.png
- gas_station_3x2.png
- park_4x2.png
- fire_station.png

effects/
- hydrant.png
- fire.png
- traffic.png
- blocked.png
- risky_road.png

vehicles/
- truck_1.png
- truck_2.png
- truck_3.png

ui/
- start_bg.png
- panel_bg.png

Quy tac variant PNG:
- Ten base trong config van hoat dong: building_1.png, road.png, truck_1.png.
- File co prefix base + dau gach duoi se duoc random theo nhom.
- Suffix _WxH noi cho game biet asset dung cho footprint nhieu o.
- Vi du: building_5_4x3.png se uu tien dung cho lot building_5 footprint 4x3.
- Vi du: building_1_house_2x2.png se random trong nhom building_1 neu lot la 2x2.
- PNG trong ui/ khong bi scale ve tile. Cac folder khac duoc scale theo footprint.

Luu y map:
- Generator uu tien city block va building footprint lon, khong con random tung o building rieng le.
- Cac phan du rong 1 o duoc bien thanh hem/sidewalk thay vi building 1x1.
- Fire duoc gan len mot cell cua building lot co duong tiep can, khong pha footprint cua asset.
