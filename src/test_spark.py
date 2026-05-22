from pyspark.sql import SparkSession

spark = (
    SparkSession.builder
    .appName("TP5 Spark Test")
    .master("local[*]")
    .getOrCreate()
)

df = spark.createDataFrame(
    [(1, "critical disk error"), (2, "user login failed")],
    ["id", "message"]
)

df.show(truncate=False)
print("Rows:", df.count())

spark.stop()
