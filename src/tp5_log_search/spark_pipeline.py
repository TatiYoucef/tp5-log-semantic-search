from __future__ import annotations

import os
from dataclasses import dataclass

from .config import Settings, load_settings


@dataclass(frozen=True)
class PreparedDataset:
    log_rows: int
    template_rows: int
    csv_dir: str
    parquet_dir: str


def prepare_dataset(
    settings: Settings | None = None,
    limit: int | None = None,
    partitions: int | None = None,
) -> PreparedDataset:
    """Prepare le dataset OpenSSH avec Spark et exporte CSV + Parquet."""

    settings = settings or load_settings()
    os.environ.setdefault("SPARK_LOCAL_IP", "127.0.0.1")

    from pyspark.sql import SparkSession
    from pyspark.sql import functions as F

    spark = (
        SparkSession.builder.appName("TP5 OpenSSH preprocessing")
        .master("local[*]")
        .config("spark.sql.shuffle.partitions", str(partitions or 8))
        .getOrCreate()
    )

    try:
        raw_rdd = spark.sparkContext.textFile(str(settings.raw_log_path))
        raw_df = raw_rdd.zipWithIndex().map(lambda item: (int(item[1]) + 1, item[0])).toDF(
            ["line_id", "raw_line"]
        )
        if limit:
            raw_df = raw_df.filter(F.col("line_id") <= int(limit))

        structured_df = (
            spark.read.option("header", True)
            .csv(str(settings.structured_csv_path))
            .select(
                F.col("LineId").cast("long").alias("line_id"),
                F.col("Content").alias("raw_message"),
                F.col("EventId").alias("event_id"),
                F.col("EventTemplate").alias("event_template"),
            )
        )
        if limit:
            structured_df = structured_df.filter(F.col("line_id") <= int(limit))

        prefix = r"^([A-Z][a-z]{2})\s+(\d{1,2})\s+(\d{2}:\d{2}:\d{2})\s+(\S+)\s+([^\[]+)\[(\d+)\]:\s+(.*)$"
        month_to_number = F.create_map(
            [item for pair in [
                (F.lit("Jan"), F.lit(1)),
                (F.lit("Feb"), F.lit(2)),
                (F.lit("Mar"), F.lit(3)),
                (F.lit("Apr"), F.lit(4)),
                (F.lit("May"), F.lit(5)),
                (F.lit("Jun"), F.lit(6)),
                (F.lit("Jul"), F.lit(7)),
                (F.lit("Aug"), F.lit(8)),
                (F.lit("Sep"), F.lit(9)),
                (F.lit("Oct"), F.lit(10)),
                (F.lit("Nov"), F.lit(11)),
                (F.lit("Dec"), F.lit(12)),
            ] for item in pair]
        )

        joined = raw_df.join(structured_df, "line_id", "left")
        with_fields = (
            joined.withColumn("month", F.regexp_extract("raw_line", prefix, 1))
            .withColumn("day", F.regexp_extract("raw_line", prefix, 2).cast("int"))
            .withColumn("time_text", F.regexp_extract("raw_line", prefix, 3))
            .withColumn("host", F.regexp_extract("raw_line", prefix, 4))
            .withColumn("service", F.trim(F.regexp_extract("raw_line", prefix, 5)))
            .withColumn("process_id", F.regexp_extract("raw_line", prefix, 6).cast("int"))
            .withColumn("parsed_content", F.regexp_extract("raw_line", prefix, 7))
            .withColumn("raw_message", F.coalesce(F.col("raw_message"), F.col("parsed_content"), F.col("raw_line")))
            .withColumn("month_num", month_to_number[F.col("month")])
            .withColumn(
                "log_timestamp",
                F.to_timestamp(
                    F.concat_ws(
                        " ",
                        F.lit(str(settings.log_year)),
                        F.col("month_num"),
                        F.col("day"),
                        F.col("time_text"),
                    ),
                    "yyyy M d HH:mm:ss",
                ),
            )
        )

        message_lower = F.lower(F.col("raw_message"))
        level = (
            F.when(
                message_lower.contains("possible break-in attempt")
                | message_lower.contains("too many authentication failures"),
                F.lit("CRITICAL"),
            )
            .when(
                message_lower.contains("failed password")
                | message_lower.contains("authentication failure")
                | message_lower.contains("fatal")
                | message_lower.contains("error")
                | message_lower.contains("invalid user")
                | message_lower.contains("user unknown"),
                F.lit("ERROR"),
            )
            .when(
                message_lower.contains("disconnect")
                | message_lower.contains("closed by")
                | message_lower.contains("preauth")
                | message_lower.contains("reverse mapping"),
                F.lit("WARNING"),
            )
            .otherwise(F.lit("INFO"))
        )

        normalized_source = F.coalesce(F.col("event_template"), F.col("raw_message"))
        final_df = (
            with_fields.withColumn("source", F.lit("OpenSSH"))
            .withColumn("level", level)
            .withColumn("normalized_message", F.lower(F.regexp_replace(normalized_source, r"\s+", " ")))
            .select(
                "line_id",
                "source",
                "log_timestamp",
                "month",
                "day",
                "time_text",
                "host",
                "service",
                "process_id",
                "level",
                "event_id",
                "raw_message",
                "normalized_message",
                "event_template",
            )
        )

        templates_df = (
            spark.read.option("header", True)
            .csv(str(settings.templates_csv_path))
            .select(
                F.col("EventId").alias("event_id"),
                F.col("EventTemplate").alias("event_template"),
                F.col("Occurrences").cast("int").alias("occurrences"),
            )
        )

        settings.processed_dir.mkdir(parents=True, exist_ok=True)
        final_df.write.mode("overwrite").partitionBy("level").parquet(str(settings.log_entries_parquet_dir))
        final_df.coalesce(1).write.mode("overwrite").option("header", True).csv(str(settings.log_entries_csv_dir))
        templates_df.coalesce(1).write.mode("overwrite").option("header", True).csv(
            str(settings.event_templates_csv_dir)
        )

        return PreparedDataset(
            log_rows=final_df.count(),
            template_rows=templates_df.count(),
            csv_dir=str(settings.log_entries_csv_dir),
            parquet_dir=str(settings.log_entries_parquet_dir),
        )
    finally:
        spark.stop()
