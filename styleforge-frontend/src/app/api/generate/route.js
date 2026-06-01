export async function POST(req) {
  try {
    const body = await req.json();

    const { prompt, occasion, gender, fabric, age } = body;

    // Build AI Prompt
    const fullPrompt = `
      Luxury fashion photoshoot,
      ${prompt},
      Occasion: ${occasion},
      Gender: ${gender},
      Fabric: ${fabric},
      Age: ${age},
      cinematic lighting,
      ultra realistic,
      luxury clothing,
      fashion editorial,
      highly detailed,
      8k
    `;

    // Encode prompt for URL
    const encodedPrompt = encodeURIComponent(fullPrompt);

    // Pollinations Image URL
    const imageUrl = `https://image.pollinations.ai/prompt/${encodedPrompt}`;

    return Response.json({
      image: imageUrl,
    });

  } catch (error) {
    console.log(error);

    return Response.json({
      error: "Something went wrong",
    });
  }
}