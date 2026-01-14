"""
Base de données PostgreSQL avec SQLAlchemy ORM
Setup complet pour le système de trading Skinport
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

Base = declarative_base()

# ================== MODÈLES DE DONNÉES ==================

class Item(Base):
    """Table des items CS2"""
    __tablename__ = 'items'
    
    id = Column(Integer, primary_key=True)
    market_hash_name = Column(String(255), unique=True, nullable=False, index=True)
    category = Column(String(100))
    type = Column(String(50))  # weapon, sticker, case, etc.
    rarity = Column(String(50))
    
    # Relations
    price_ticks = relationship("PriceTick", back_populates="item", cascade="all, delete-orphan")
    signals = relationship("Signal", back_populates="item", cascade="all, delete-orphan")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Item(id={self.id}, name='{self.market_hash_name}')>"


class PriceTick(Base):
    """Table des prix historiques (ticks)"""
    __tablename__ = 'price_ticks'
    
    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey('items.id'), nullable=False, index=True)
    
    timestamp = Column(DateTime, nullable=False, index=True, default=datetime.utcnow)
    price = Column(Float, nullable=False)  # Prix en EUR
    volume = Column(Integer)  # Nombre de ventes
    quantity = Column(Integer)  # Stock disponible
    source = Column(String(50), default='skinport')  # skinport, steam, etc.
    
    # Relation
    item = relationship("Item", back_populates="price_ticks")
    
    # Index composite pour requêtes rapides
    __table_args__ = (
        Index('idx_item_timestamp', 'item_id', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<PriceTick(item_id={self.item_id}, price={self.price}, timestamp={self.timestamp})>"


class Signal(Base):
    """Table des signaux de trading détectés"""
    __tablename__ = 'signals'
    
    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey('items.id'), nullable=False, index=True)
    
    timestamp = Column(DateTime, nullable=False, index=True, default=datetime.utcnow)
    signal_type = Column(String(50), nullable=False)  # UNDERPRICED, MOMENTUM, REVERSAL, TRAP
    
    # Métriques
    z_score = Column(Float)
    volume_24h = Column(Integer)
    edge_net = Column(Float)  # Edge net après frais (%)
    spread = Column(Float)
    momentum_1h = Column(Float)
    momentum_6h = Column(Float)
    momentum_24h = Column(Float)
    
    confidence = Column(Float)  # Score de confiance 0-100
    reason = Column(String(500))  # Explication du signal
    
    # Statut
    alerted = Column(Boolean, default=False)  # Alerte envoyée ?
    executed = Column(Boolean, default=False)  # Trade exécuté ?
    result = Column(String(50))  # WIN, LOSS, PENDING, CANCELLED
    
    # Relation
    item = relationship("Item", back_populates="signals")
    
    __table_args__ = (
        Index('idx_signal_type_timestamp', 'signal_type', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<Signal(id={self.id}, type={self.signal_type}, item_id={self.item_id})>"


class Trade(Base):
    """Table des trades réellement exécutés (pour tracking performance)"""
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    signal_id = Column(Integer, ForeignKey('signals.id'), index=True)
    item_id = Column(Integer, ForeignKey('items.id'), nullable=False, index=True)
    
    # Détails du trade
    buy_timestamp = Column(DateTime, nullable=False)
    buy_price = Column(Float, nullable=False)
    sell_timestamp = Column(DateTime)
    sell_price = Column(Float)
    quantity = Column(Integer, default=1)
    
    # Frais
    buy_fee = Column(Float)
    sell_fee = Column(Float)
    
    # Performance
    profit_gross = Column(Float)  # Profit brut
    profit_net = Column(Float)  # Profit net après frais
    profit_pct = Column(Float)  # % de profit
    
    status = Column(String(20), default='OPEN')  # OPEN, CLOSED, CANCELLED
    notes = Column(String(500))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Trade(id={self.id}, item_id={self.item_id}, profit_net={self.profit_net})>"


class AlertLog(Base):
    """Log des alertes envoyées (anti-spam)"""
    __tablename__ = 'alert_logs'
    
    id = Column(Integer, primary_key=True)
    signal_id = Column(Integer, ForeignKey('signals.id'))
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    alert_type = Column(String(50))  # discord, telegram, email
    recipient = Column(String(100))
    message = Column(String(1000))
    
    success = Column(Boolean, default=True)
    error = Column(String(500))
    
    def __repr__(self):
        return f"<AlertLog(id={self.id}, type={self.alert_type}, timestamp={self.timestamp})>"


# ================== CLASSE DE GESTION DB ==================

class DatabaseManager:
    """Gestionnaire de base de données"""
    
    def __init__(self, connection_string: str = None):
        """
        Initialize database connection
        
        Args:
            connection_string: PostgreSQL connection string
                Ex: "postgresql://user:password@localhost:5432/skinport_trading"
                Par défaut: utilise SQLite en local pour tests
        """
        if connection_string is None:
            # Mode dev : SQLite local
            connection_string = "sqlite:///skinport_trading.db"
            print("⚠️  Mode DEV : utilisation de SQLite local")
        
        self.engine = create_engine(connection_string, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def create_tables(self):
        """Crée toutes les tables"""
        Base.metadata.create_all(self.engine)
        print("✅ Tables créées avec succès")
    
    def drop_tables(self):
        """⚠️ Supprime toutes les tables (ATTENTION !)"""
        Base.metadata.drop_all(self.engine)
        print("⚠️  Toutes les tables ont été supprimées")
    
    def get_session(self):
        """Retourne une nouvelle session"""
        return self.SessionLocal()
    
    # ========== MÉTHODES UTILES ==========
    
    def add_item(self, session, market_hash_name: str, category: str = None, 
                 type: str = None, rarity: str = None):
        """Ajoute un item s'il n'existe pas déjà"""
        item = session.query(Item).filter_by(market_hash_name=market_hash_name).first()
        
        if item is None:
            item = Item(
                market_hash_name=market_hash_name,
                category=category,
                type=type,
                rarity=rarity
            )
            session.add(item)
            session.commit()
            print(f"✅ Item ajouté: {market_hash_name}")
        
        return item
    
    def add_price_tick(self, session, item_id: int, price: float, 
                      volume: int = None, quantity: int = None, 
                      timestamp: datetime = None):
        """Ajoute un tick de prix"""
        tick = PriceTick(
            item_id=item_id,
            price=price,
            volume=volume,
            quantity=quantity,
            timestamp=timestamp or datetime.utcnow()
        )
        session.add(tick)
        session.commit()
        return tick
    
    def add_signal(self, session, signal_data: dict):
        """Ajoute un signal de trading"""
        signal = Signal(**signal_data)
        session.add(signal)
        session.commit()
        return signal
    
    def get_item_by_name(self, session, market_hash_name: str):
        """Récupère un item par son nom"""
        return session.query(Item).filter_by(market_hash_name=market_hash_name).first()
    
    def get_recent_prices(self, session, item_id: int, hours: int = 24):
        """Récupère les prix récents d'un item"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return session.query(PriceTick).filter(
            PriceTick.item_id == item_id,
            PriceTick.timestamp >= cutoff
        ).order_by(PriceTick.timestamp.desc()).all()
    
    def get_unsent_signals(self, session, limit: int = 10):
        """Récupère les signaux non encore alertés"""
        return session.query(Signal).filter(
            Signal.alerted == False,
            Signal.signal_type != 'TRAP'
        ).order_by(Signal.timestamp.desc()).limit(limit).all()
    
    def mark_signal_alerted(self, session, signal_id: int):
        """Marque un signal comme ayant été alerté"""
        signal = session.query(Signal).get(signal_id)
        if signal:
            signal.alerted = True
            session.commit()


# ================== EXEMPLE D'UTILISATION ==================

if __name__ == "__main__":
    from datetime import timedelta
    
    # 1. Initialiser la DB
    print("\n" + "="*60)
    print("INITIALISATION BASE DE DONNÉES")
    print("="*60 + "\n")
    
    # Mode SQLite local pour dev
    db = DatabaseManager()
    
    # Créer les tables
    db.create_tables()
    
    # 2. Ajouter des données de test
    print("\n" + "="*60)
    print("INSERTION DE DONNÉES DE TEST")
    print("="*60 + "\n")
    
    session = db.get_session()
    
    # Ajouter des items
    item1 = db.add_item(
        session, 
        market_hash_name="AK-47 | Redline (Field-Tested)",
        category="weapon",
        type="rifle",
        rarity="classified"
    )
    
    item2 = db.add_item(
        session,
        market_hash_name="AWP | Asiimov (Field-Tested)",
        category="weapon",
        type="sniper",
        rarity="covert"
    )
    
    # Ajouter des prix historiques
    now = datetime.utcnow()
    for i in range(20):
        timestamp = now - timedelta(hours=i)
        price = 30.0 + (i % 5) - 2  # Prix qui varie
        db.add_price_tick(
            session,
            item_id=item1.id,
            price=price,
            volume=5 + (i % 3),
            timestamp=timestamp
        )
    
    print(f"✅ 20 prix historiques ajoutés pour {item1.market_hash_name}")
    
    # Ajouter un signal
    signal_data = {
        'item_id': item1.id,
        'signal_type': 'UNDERPRICED',
        'z_score': -2.3,
        'volume_24h': 15,
        'edge_net': 4.5,
        'spread': 0.08,
        'confidence': 85.0,
        'reason': 'Prix 2.3 écarts-types sous moyenne, volume OK'
    }
    signal = db.add_signal(session, signal_data)
    print(f"✅ Signal créé: {signal.signal_type} pour item {signal.item_id}")
    
    # 3. Requêtes de test
    print("\n" + "="*60)
    print("TESTS DE REQUÊTES")
    print("="*60 + "\n")
    
    # Récupérer les prix récents
    recent_prices = db.get_recent_prices(session, item1.id, hours=12)
    print(f"📊 {len(recent_prices)} prix trouvés sur les 12 dernières heures")
    print(f"   Prix actuel: {recent_prices[0].price:.2f}€")
    print(f"   Prix moyen: {sum(p.price for p in recent_prices) / len(recent_prices):.2f}€")
    
    # Récupérer signaux non alertés
    unsent = db.get_unsent_signals(session)
    print(f"\n🔔 {len(unsent)} signaux en attente d'alerte")
    for s in unsent:
        print(f"   - {s.signal_type}: {s.item.market_hash_name} (confiance: {s.confidence}%)")
    
    session.close()
    
    print("\n" + "="*60)
    print("✅ SETUP COMPLET TERMINÉ")
    print("="*60)
    print("\nBase de données créée: skinport_trading.db")
    print("Tu peux maintenant utiliser DatabaseManager dans ton code principal\n")