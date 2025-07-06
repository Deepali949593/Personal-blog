from supabase import create_client, Client

url = "https://xcikopnxwqsjvzzxmqjy.supabase.co"  # Replace this
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhjaWtvcG54d3FzanZ6enhtcWp5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTE4MTA3NDEsImV4cCI6MjA2NzM4Njc0MX0.W6IKw5RXCb5gwImsB6cAwPRY-LLxzW-oq2zm4pOORq0"                         # Replace this

supabase: Client = create_client(url, key)
