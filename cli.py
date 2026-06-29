import typer
from datetime import date, datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session, joinedload
from helpmeet_licenses.database import SessionLocal
from helpmeet_licenses.keys import generate_license_key
from helpmeet_licenses.models import Customer, License, LicenseEvent
from helpmeet_licenses.auth import hash_key

app = typer.Typer(help="Gestión de licencias Helpmeet")

def _db() -> Session:
    return SessionLocal()

@app.command("create-customer")
def create_customer(
    email: str = typer.Option(..., help="Email del cliente"),
    name: Optional[str] = typer.Option(None, help="Nombre"),
):
    """Crea un nuevo cliente."""
    db = _db()
    try:
        customer = Customer(email=email, name=name)
        db.add(customer)
        db.commit()
        db.refresh(customer)
        typer.echo(f"Creado: ID={customer.id} email={customer.email}")
    finally:
        db.close()

@app.command("create-license")
def create_license(
    customer_id: int = typer.Option(..., help="ID del cliente"),
    plan: str = typer.Option("personal", help="Plan: personal | pro | team"),
    updates_until: Optional[str] = typer.Option(None, help="Fecha YYYY-MM-DD"),
):
    """Crea una licencia y muestra la product key (solo una vez)."""
    if updates_until:
        try:
            until = date.fromisoformat(updates_until)
        except ValueError:
            typer.echo(f"Fecha invalida: '{updates_until}'. Usa formato YYYY-MM-DD.", err=True)
            raise typer.Exit(1)
    else:
        until = None

    db = _db()
    try:
        customer = db.get(Customer, customer_id)
        if not customer:
            typer.echo(f"Cliente {customer_id} no encontrado", err=True)
            raise typer.Exit(1)
        key = generate_license_key()
        lic = License(
            customer_id=customer_id,
            key_hash=hash_key(key),
            key_last4=key[-4:],
            plan=plan,
            updates_until=until,
        )
        db.add(lic)
        db.flush()  # populates lic.id
        db.add(LicenseEvent(license_id=lic.id, event_type="created", event_metadata={}))
        db.commit()
        db.refresh(lic)
        typer.echo(f"\n{'='*50}")
        typer.echo("COPIA ESTA KEY - no se puede recuperar despues")
        typer.echo(f"{'='*50}")
        typer.echo(f"  {key}")
        typer.echo(f"{'='*50}\n")
        typer.echo(f"Licencia ID={lic.id} | Plan={plan} | Cliente={customer.email}")
    finally:
        db.close()

@app.command("list-licenses")
def list_licenses(status: Optional[str] = typer.Option(None)):
    """Lista todas las licencias."""
    db = _db()
    try:
        q = db.query(License).options(joinedload(License.customer))
        if status:
            q = q.filter(License.status == status)
        licenses = q.all()
        if not licenses:
            typer.echo("Sin licencias.")
            return
        for lic in licenses:
            typer.echo(
                f"ID={lic.id} | ...{lic.key_last4} | {lic.plan} | {lic.status} "
                f"| {lic.customer.email if lic.customer else '?'}"
            )
    finally:
        db.close()

@app.command("revoke-license")
def revoke_license(license_id: int = typer.Option(...)):
    """Revoca una licencia."""
    db = _db()
    try:
        lic = db.get(License, license_id)
        if not lic:
            typer.echo(f"Licencia {license_id} no encontrada", err=True)
            raise typer.Exit(1)
        lic.status = "revoked"
        lic.revoked_at = datetime.now(tz=timezone.utc)
        db.add(LicenseEvent(license_id=lic.id, event_type="revoked", event_metadata={}))
        db.commit()
        typer.echo(f"Licencia {license_id} revocada.")
    finally:
        db.close()

if __name__ == "__main__":
    app()
