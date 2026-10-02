from pydantic_settings import BaseSettings, SettingsConfigDict

# Valeur sentinelle de dev, signalée au démarrage : la vraie valeur vient de JWT_SECRET
SECRET_JWT_DEV = "dev-uniquement-a-remplacer-en-production"  # noqa: S105


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://stockpredict:stockpredict@localhost:5432/stockpredict"
    app_version: str = "0.1.0"

    # Session (D-12)
    jwt_secret: str = SECRET_JWT_DEV
    session_duree_heures: int = 8
    # Cookie « Secure » : true dès que l'app est servie en HTTPS hors localhost (D-24)
    cookie_secure: bool = False
    # Adresse IP réelle lue dans X-Forwarded-For (derrière le proxy Vite / le tunnel)
    faire_confiance_au_proxy: bool = True

    # Verrouillage (RG-15)
    echecs_avant_verrouillage: int = 5
    duree_verrouillage_minutes: int = 15

    # Comptes de démonstration (npm run seed), jamais en production
    demo_mot_de_passe: str | None = None


settings = Settings()
