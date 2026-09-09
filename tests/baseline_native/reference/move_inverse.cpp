#include "universe.hpp"
#include <algorithm>
#include <set>
#include <string>
#include <iostream>

using Shape=std::set<std::array<int,4>>;
std::array<int,4> key(Tetra::Label t) {
    std::array<int,4> a; for(int i=0;i<4;i++) a[i]=t->vs[i];
    std::sort(a.begin(),a.end()); return a;
}
Shape shape() { Shape s; for(auto t:Universe::tetrasAll) s.insert(key(t)); return s; }
int main(int argc,char** argv) {
    if(argc!=3) return 2;
    Universe::initialize(argv[1],"inverse",3,1);
    auto before=shape(); std::string kind=argv[2]; bool done=false;
    if(kind=="26") {
        std::set<int> old; for(auto v:Universe::verticesAll) old.insert(v);
        Universe::move26(*Universe::tetras31.begin());
        Vertex::Label added=-1; for(auto v:Universe::verticesAll) if(!old.count(v)) added=v;
        assert(added>=0); Universe::check();
        done=Universe::move62(added);
    } else if(kind=="44") {
        for(auto t:Universe::tetras31) {
            for(int i=0;i<3;i++) {
                auto n=t->tnbr[i];
                if(!n->is31() || !t->tnbr[3]->neighborsTetra(n->tnbr[3])) continue;
                if(Universe::move44(t,n)) { Universe::check(); done=Universe::move44(t,n); goto finish; }
            }
        }
    } else if(kind=="23u") {
        for(auto t:Universe::tetras31) {
            for(int i=0;i<3;i++) {
                auto n=t->tnbr[i]; if(!n->is22()) continue;
                if(Universe::move23u(t,n)) {
                    Universe::check();
                    for(auto q:Universe::tetras31) if(!before.count(key(q))) {
                        done=Universe::move32u(q,q->tnbr[2],q->tnbr[1]); goto finish;
                    }
                }
            }
        }
    } else if(kind=="23d") {
        for(auto t:Universe::tetrasAll) {
            if(!t->is13()) continue;
            for(int i=1;i<4;i++) {
                auto n=t->tnbr[i]; if(!n->is22()) continue;
                if(Universe::move23d(t,n)) {
                    Universe::check();
                    for(auto q:Universe::tetrasAll) if(q->is13() && !before.count(key(q))) {
                        // Orientation follows move23d's explicit output incidence.
                        done=Universe::move32d(q,q->tnbr[3],q->tnbr[2]); goto finish;
                    }
                }
            }
        }
    }
finish:
    if(!done) { std::cerr<<"No invertible candidate for "<<kind<<"\n"; return 3; }
    Universe::check();
    if(shape()!=before) { std::cerr<<"Inverse changed simplices\n"; return 4; }
    std::cout<<"PASS inverse "<<kind<<"\n";
}
