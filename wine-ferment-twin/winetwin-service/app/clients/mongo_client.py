class MongoClientWrapper:
    def __init__(self, uri): self.uri=uri
    def status(self): return {"configured": bool(self.uri)}
