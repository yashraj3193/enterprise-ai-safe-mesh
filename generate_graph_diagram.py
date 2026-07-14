import sys
import os

# 🌟 SAFE & SIMPLE: Agar aap script ko project root folder se run kar rahe hain,
# toh Python automatic graph.py ko dhund lega bina kisi manual path hardcoding ke!
try:
    print("🔄 Connecting to 'graph.py' and compiling LangGraph pipeline...")
    from graph import mesh_builder
    
    # 🌟 StateGraph builder compile ho raha hai (sirf graph flow draw karne ke liye checkpointer ki need nahi hai)
    compiled_graph = mesh_builder.compile()
    
    print("🎨 Generating visual Mermaid diagram via HTTP API...")
    # LangGraph internally Mermaid ink API use karta hai graph layout render karne ke liye.
    # Iske liye aapke local system par Graphviz install hone ki bilkul zarurat nahi hai!
    png_data = compiled_graph.get_graph().draw_mermaid_png()
    
    output_path = "architecture_graph.png"
    with open(output_path, "wb") as f:
        f.write(png_data)
        
    print(f"\n🎉 SUCCESS! High-resolution architecture diagram saved as: '{output_path}'")
    print("💡 Ab aap is diagram ko direct apne README.md ke sabse upar showcase kar sakte ho!")

except ImportError as e:
    print(f"\n❌ Import Error: Kya aap is script ko 'enterprise-safe-ai-mesh' folder ke andar se hi run kar rahe hain?")
    print(f"   Dhyan rakhein ki 'graph.py' isi same directory mein honi chahiye. Error Detail: {e}")
except Exception as e:
    print(f"\n❌ Failed to generate graph image: {e}")