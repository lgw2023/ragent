uv run python singlefile.py parse example/成人高血压食养指南_2022.pdf example/成人高血压食养指南_2022_md example/demo_diet_kg &> example/成人高血压食养指南_2022.log
cp -r example/demo_diet_kg example/demo_diet_kg_1
uv run python singlefile.py parse example/成人肥胖食养指南_2024.pdf example/成人肥胖食养指南_2024_md example/demo_diet_kg &> example/成人肥胖食养指南_2024.log
cp -r example/demo_diet_kg example/demo_diet_kg_2
uv run python singlefile.py parse example/中国居民膳食指南_2022.pdf example/中国居民膳食指南_2022_md example/demo_diet_kg &> example/中国居民膳食指南_2022.log
cp -r example/demo_diet_kg example/demo_diet_kg_3

uv run python singlefile.py parse example/GBT1354-2018bz.pdf example/GBT1354-2018bz_md example/demo_diet_kg &> example/GBT1354-2018bz.log
cp -r example/demo_diet_kg example/demo_diet_kg_4
uv run python singlefile.py parse example/GBT22106-2008dz.pdf example/GBT22106-2008dz_md example/demo_diet_kg &> example/GBT22106-2008dz.log
cp -r example/demo_diet_kg example/demo_diet_kg_5

# uv run python singlefile.py parse example/core-data_recipe_compact.csv example_test/demo_diet_kg rag
# cp -r example/demo_diet_kg example/demo_diet_kg_6

# export WIDE_TABLE_ENTITY_TYPE=food
# export WIDE_TABLE_ENTITY_NAME_COLUMN="Main food description"
# export WIDE_TABLE_EXCLUDED_COLUMNS="Food code,WWEIA Category number"
# export WIDE_TABLE_SHEET_NAME="FNDDS Nutrient Values"
# python singlefile.py parse "example/2021-2023 FNDDS At A Glance - FNDDS Nutrient Values.xlsx" "example/demo_diet_kg" rag
# cp -r example/demo_diet_kg example/demo_diet_kg_7

cp .env .env_bak
cp .env_onehop .env

uv run python singlefile.py onehop example/demo_diet_kg_5 "35 岁男 170cm/86kg/腰围95，3 次血压 146/92、144/90、148/94，一天 2250 千卡减到 1750 够吗？" hybrid &> script/0403_q1.kg_5.v1.md
uv run python singlefile.py onehop example/demo_diet_kg_5 "今天油24g、盐4.8g、添加糖22g、酒精18g，先戒哪个？" hybrid &> script/0403_q2.kg_5.v1.md
uv run python singlefile.py onehop example/demo_diet_kg_5 "谷类240g其中全谷杂豆60g、薯类80g、蔬菜360g里深色150g、水果250g，肥胖及高血压并症患者这样吃达标吗？" hybrid &> script/0403_q3.kg_5.v1.md
uv run python singlefile.py onehop example/demo_diet_kg_5 "我有点胖，现在90kg， 想 6 个月减到 75kg，会不会太猛？" hybrid &> script/0403_q4.kg_5.v1.md
uv run python singlefile.py onehop example/demo_diet_kg_5 "酱油16g+鸡精5g，再额外放2g盐，如果全摄入的话，这一天是不是已经超了？" hybrid &> script/0403_q5.kg_5.v1.md
uv run python singlefile.py onehop example/demo_diet_kg_5 "早餐燕麦粥+牛奶+鸡蛋+西芹花生米，午餐杂粮饭+鸡翅根+土豆丝+菠菜+紫菜蛋汤，晚餐米饭+豆腐+香菇油菜+鲈鱼+苹果，每周都这样吃的话，食物种类够吗？" hybrid &> script/0403_q6.kg_5.v1.md
uv run python singlefile.py onehop example/demo_diet_kg_5 "下午多吃了 150 千卡点心，先快走 30 分钟，再爬楼多久能补回来？" hybrid &> script/0403_q7.kg_5.v1.md

