"""
Import a physics graph dataset into Neo4j Aura using batched UNWIND Cypher.
Run from the project root:

    python import_to_neo4j.py --dataset physics_small
    python import_to_neo4j.py --dataset physics
"""
import csv
import os
import asyncio
import argparse
import time
from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

NEO4J_URL  = os.environ["NEO4J_URL"]
NEO4J_USER = os.environ["NEO4J_USER"]
NEO4J_PASS = os.environ["NEO4J_PASSWORD"]

parser = argparse.ArgumentParser()
parser.add_argument(
    "--dataset",
    type=str,
    default="physics_small",
    help="Dataset folder name under datasets/ and the Neo4j node label to use",
)
args = parser.parse_args()

DATASET   = args.dataset
NODES_CSV = os.path.join("datasets", DATASET, "nodes.csv")
EDGES_CSV = os.path.join("datasets", DATASET, "edges.csv")
BATCH_SIZE = 500


async def count_existing(session):
    r = await session.run(f"MATCH (n:{DATASET}) RETURN count(n) AS c")
    rec = await r.single()
    return rec["c"]


async def import_nodes(driver):
    print(f"Reading {NODES_CSV} ...")
    rows = []
    with open(NODES_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "id":          row["id:ID(physics)"],
                "node_type":   row["node_type"],
                "name":        row["name"],
                "description": row["description"],
            })
    total = len(rows)
    print(f"  {total:,} nodes to import under label :{DATASET}")

    async with driver.session() as session:
        existing = await count_existing(session)
        if existing >= total:
            print(f"  Nodes already loaded ({existing:,}), skipping.")
            return

    # Each node gets TWO labels: :<DATASET> and :<DATASET>:<node_type>
    # e.g. :physics_small:author — so the LLM can filter by type in Cypher.
    # We group by node_type and run one UNWIND per type to set labels dynamically.
    by_type: dict = {}
    for r in rows:
        by_type.setdefault(r["node_type"], []).append(r)

    for node_type, batch_rows in by_type.items():
        cypher = f"""
        UNWIND $rows AS row
        MERGE (n:{DATASET} {{id: row.id}})
        SET n:{DATASET}:{node_type},
            n.node_type   = row.node_type,
            n.name        = row.name,
            n.description = row.description
        """
        for i in range(0, len(batch_rows), BATCH_SIZE):
            async with driver.session() as session:
                await session.run(cypher, rows=batch_rows[i : i + BATCH_SIZE])
        print(f"  imported {len(batch_rows):,} {node_type} nodes")
    print(f"  Done nodes in total: {total:,}")


async def import_edges(driver):
    print(f"Reading {EDGES_CSV} ...")
    rows = []
    with open(EDGES_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "src":      row[":START_ID(physics)"],
                "dst":      row[":END_ID(physics)"],
                "relation": row["relation:TYPE"],
            })
    total = len(rows)
    print(f"  {total:,} edges to import")

    # Neo4j relationship types must be literals — cannot be passed as parameters.
    # Group by relation type and emit one UNWIND per type.
    by_rel: dict = {}
    for r in rows:
        by_rel.setdefault(r["relation"], []).append(r)

    t0 = time.time()
    done = 0
    for rel_type, rel_rows in by_rel.items():
        cypher = f"""
        UNWIND $rows AS row
        MATCH (a:{DATASET} {{id: row.src}})
        MATCH (b:{DATASET} {{id: row.dst}})
        MERGE (a)-[r:{rel_type}]->(b)
        """
        for i in range(0, len(rel_rows), BATCH_SIZE):
            async with driver.session() as session:
                await session.run(cypher, rows=rel_rows[i : i + BATCH_SIZE])
            done += min(BATCH_SIZE, len(rel_rows) - i)
            elapsed = time.time() - t0
            rate = done / elapsed if elapsed > 0 else 0
            eta = (total - done) / rate if rate > 0 else 0
            print(f"  edges {done:>9,}/{total:,}  [{rel_type}]  {rate:,.0f}/s  ETA {eta:.0f}s", end="\r")
        print(f"\n  imported {len(rel_rows):,} [{rel_type}] edges")
    print(f"  Done edges in {time.time()-t0:.0f}s")


async def create_index(driver):
    print(f"Creating index on {DATASET}.id ...")
    async with driver.session() as session:
        await session.run(
            f"CREATE INDEX IF NOT EXISTS FOR (n:{DATASET}) ON (n.id)"
        )
    print("  Index created.")


async def verify(driver):
    async with driver.session() as session:
        r = await session.run(f"MATCH (n:{DATASET}) RETURN count(n) AS node_count")
        nodes = (await r.single())["node_count"]
        r = await session.run("MATCH ()-[r]->() RETURN count(r) AS edge_count")
        edges = (await r.single())["edge_count"]
    print(f"\nVerification: {nodes:,} nodes, {edges:,} edges in Neo4j")


async def main():
    driver = AsyncGraphDatabase.driver(NEO4J_URL, auth=(NEO4J_USER, NEO4J_PASS))
    try:
        async with driver.session() as s:
            r = await s.run("RETURN 1 AS n")
            await r.single()
        print(f"Neo4j connection OK  ({NEO4J_URL})\n")

        await import_nodes(driver)
        await create_index(driver)
        await import_edges(driver)
        await verify(driver)
    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(main())
