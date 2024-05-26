from http.client import HTTPException
from fastapi import FastAPI
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
import asyncio
from contextlib import asynccontextmanager
from sqlmodel import SQLModel
import logging

from app import gamer_pb2


logging.basicConfig(level=logging.INFO)

KAFKA_BROKER = "broker:19092"
KAFKA_TOPIC = "gamers"
KAFKA_CONSUMER_GROUP_ID = "gamers-consumer-group"

class GamePlayersRegistration(SQLModel):
    player_name: str
    age: int
    email: str
    phone_number: str


async def consume():
    # Milestone: CONSUMER INTIALIZE
    consumer = AIOKafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BROKER
    )

    await consumer.start()
    try:
        async for msg in consumer:
            logging.info("RAW MESSAGE: %s", msg.value)
            deserialize_message = gamer_pb2.GamePlayers()
            deserialize_message.ParseFromString(msg.value)
            logging.info("DERSERLIZSEA: %s", deserialize_message)

    finally:
        await consumer.stop()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting consumer")
    asyncio.create_task(consume())
    yield
    print("Stopping consumer")

app = FastAPI(lifespan=lifespan, 
              title="Hello Kong With FastAPI",
              version="0.0.1",
              root_path="/gamer")


@app.get("/")
def hello():
    return {"Hello": "World"}


@app.post("/register-player")
async def register_new_player(player_data: GamePlayersRegistration):
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BROKER)

    player_data_prot = gamer_pb2.GamePlayers(
        player_name=player_data.player_name, age=player_data.age, email=player_data.email, phone_number=player_data.phone_number)
    print("player_data_prot", player_data_prot)

    player_data_prot_serialized = player_data_prot.SerializeToString()
    print("player_data_prot_serialized", player_data_prot_serialized)

    await producer.start()

    try:
        await producer.send_and_wait(KAFKA_TOPIC, player_data_prot_serialized)
    finally:
        await producer.stop()

    return player_data.model_dump_json()

# @app.get("/consumer")
# async def consume_messages():
#     consumer = AIOKafkaConsumer(
#         settings.KAFKA_TOPIC, # type: ignore
#         bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVER, # type: ignore
#         group_id=settings.KAFKA_CONSUMER_GROUP_ID, # type: ignore
#         #key_deserializer=key_deserializer,
#         #value_deserializer=value_deserializer,
#         auto_offset_reset='latest',  # Start reading from the earliest offset if no offset is committed
#     )
#     await consumer.start()

#     try:
#         # Fetch a single message with a timeout
#         msg = await asyncio.wait_for(consumer.getone(), timeout=10.0)
#         tp = TopicPartition(msg.topic, msg.partition) # type: ignore

#         # Current position
#         position = await consumer.position(tp)
#         logging.info(f"Current position: {position}")
        
#         # Committed offset
#         committed = await consumer.committed(tp)
#         logging.info(f"Committed offset: {committed}")

#         logging.info(
#             "{}:{:d}:{:d}: key={} value={} timestamp_ms={}".format(
#                 msg.topic, msg.partition, msg.offset, msg.key, msg.value,
#                 msg.timestamp)
#         )
#         return {"raw_message": msg, "offset": msg.offset, "key": msg.key, "value": msg.value}
#     except asyncio.TimeoutError:
#         logging.warning("No messages received within the timeout period")
#         raise HTTPException(status_code=408, detail="No messages received within the timeout period")
#     finally:
#         logging.info("Finally Stopping consumer")
#         await consumer.stop()
