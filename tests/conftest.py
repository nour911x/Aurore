import os
import tempfile


os.environ["AURORE_DONNEES"] = tempfile.mkdtemp(prefix="aurore-tests-")
os.environ["GROQ_KEY"] = "cle-de-test"
