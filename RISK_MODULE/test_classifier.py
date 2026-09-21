from sentence_transformers import CrossEncoder
import numpy as np

model = CrossEncoder(
    "cross-encoder/nli-deberta-v3-small"
)

labels = [

"Termination Clause",

"Rights Waiver",

"Financial Risk",

"Auto Renewal",

"Power of Attorney",

"Safe Clause"

]

def classify_clause(clause):

    pairs=[]

    for label in labels:

        pairs.append(
            [clause,label]
        )

    scores=model.predict(
        pairs
    )

    scores=np.array(
        scores
    )

    best_index=int(
        np.argmax(scores)
    )

    return{

        "category":labels[
            best_index
        ],

        "confidence":round(
            float(
                scores[
                    best_index
                ]
            ),
            2
        )

    }